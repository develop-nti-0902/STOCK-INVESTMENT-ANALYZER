"""スクリーニング戦略の抽象基底クラスを定義するモジュール。"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import date
from typing import Any, List, Optional

from app.services.screening.models import ScreeningConfig, ScreeningResult

logger = logging.getLogger(__name__)


class BaseScreeningStrategy(ABC):
    """スクリーニング戦略の抽象基底クラス。

    サブクラスは業種別設定に基づくカスタム実装を提供します。
    """

    def __init__(self, config: ScreeningConfig):
        """初期化。

        Args:
            config: スクリーニング設定（業種別）
        """
        self._config = config
        self._thresholds = config.thresholds
        self._score_config = config.score_config

    @property
    def config(self) -> ScreeningConfig:
        """スクリーニング設定を取得。"""
        return self._config

    @abstractmethod
    async def evaluate(
        self, sec_code: str, _evaluation_date: date, **kwargs: Any
    ) -> ScreeningResult:
        """単一銘柄についてスクリーニングを行い ScreeningResult を返します。

        Args:
            sec_code: 証券コード
            _evaluation_date: 評価実行日
            **kwargs: サブクラスで追加のパラメータを受け取り可能

        Returns:
            ScreeningResult

        Note:
            具体的な履歴データ取得は、呼び出し側で用意し、
            evaluate_with_history メソッドで渡してください。
        """

    # pylint: disable=R0913,R0917
    async def evaluate_with_history(
        self,
        sec_code: str,
        evaluation_date: date,  # pylint: disable=W0613
        divs: List[Any],
        eps: List[Any],
        cfs: List[Any],
        stabs: List[Any],
    ) -> ScreeningResult:
        """与えられた履歴データを使用してスクリーニングを実行。

        Args:
            sec_code: 証券コード
            evaluation_date: 評価実行日
            divs: 配当履歴
            eps: EPS履歴
            cfs: キャッシュフロー履歴
            stabs: 安定性データ（売上、営業利益、営業マージン）

        Returns:
            ScreeningResult
        """
        failed: List[str] = []

        # 必須条件チェック
        if not self._check_dividend_continuity(divs):
            failed.append("dividend_continuity")
        if not self._check_eps_health(eps):
            failed.append("eps_health")
        if not self._check_operating_cf(cfs):
            failed.append("operating_cf")

        pass_required = len(failed) == 0

        # スコア計算
        sd = self._score_dividend(divs)
        se = self._score_eps(eps)
        ss = self._score_stability(stabs)
        sp = self._score_profitability(stabs)

        status = self._resolve_status(pass_required, sd + se + ss + sp)
        fiscal_year = self._extract_latest_fiscal_year_end(divs, eps, stabs)

        return ScreeningResult(
            sec_code=sec_code,
            pass_required=pass_required,
            total_score=sd + se + ss + sp,
            score_dividend=sd,
            score_eps=se,
            score_stability=ss,
            score_profitability=sp,
            status=status,
            failed_conditions=failed,
            fiscal_year_end=fiscal_year,
        )

    # ================ 必須条件チェック ================

    def _check_dividend_continuity(self, divs: List[Any]) -> bool:
        """配当継続性をチェック。"""
        if not divs:
            return False

        raw_vals = [getattr(d, "dividend_per_share", None) for d in divs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]

        if len(vals) < 2:
            return False

        # 減配していないことを確認
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                return False

        # N年以上連続増配（または現状維持）の期間が存在
        max_consecutive_increase = 1
        current_consecutive_increase = 1
        for i in range(1, len(vals)):
            if vals[i] >= vals[i - 1]:
                current_consecutive_increase += 1
                max_consecutive_increase = max(
                    max_consecutive_increase, current_consecutive_increase
                )
            else:
                current_consecutive_increase = 1

        return max_consecutive_increase >= self._thresholds.dividend_min_consecutive_increase

    def _check_eps_health(self, eps: List[Any]) -> bool:
        """EPS の健全性をチェック。"""
        if not eps:
            return False

        raw_vals = [getattr(e, "eps", None) for e in eps]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]

        # EPS が負またはゼロでないこと
        if any(v <= 0 for v in vals):
            return False

        # 直近2年で連続減少していないことを確認
        dec_flags = []
        for i in range(1, len(vals)):
            dec_flags.append(vals[i] < vals[i - 1])

        max_consecutive_decline = 0
        current_decline = 0
        for flag in dec_flags:
            if flag:
                current_decline += 1
                max_consecutive_decline = max(max_consecutive_decline, current_decline)
            else:
                current_decline = 0

        if max_consecutive_decline > self._thresholds.eps_max_consecutive_decline:
            return False

        # 減少時の最大許容率チェック
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                decrease_rate = (vals[i - 1] - vals[i]) / vals[i - 1]
                if decrease_rate >= self._thresholds.eps_decline_max_rate:
                    return False

        return True

    def _check_operating_cf(self, cfs: List[Any]) -> bool:
        """営業キャッシュフローをチェック。"""
        if not cfs:
            return False

        raw_vals = [getattr(c, "operating_cf", None) for c in cfs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        positive_years = sum(1 for v in vals if v > 0)

        return positive_years >= self._thresholds.cf_min_positive_years

    # ================ スコア計算 ================

    def _score_dividend(self, divs: List[Any]) -> int:
        """配当スコアを計算。"""
        score = 0
        raw_vals = [getattr(d, "dividend_per_share", None) for d in divs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]

        if len(vals) < 2:
            return 0

        # 過去N年間連続増配（またはそれ以上、現状維持を含む）
        all_increasing = all(vals[i] >= vals[i - 1] for i in range(1, len(vals)))
        if all_increasing:
            score += self._score_config.dividend_all_increase_score

        # 過去N年間平均増配率が閾値以上
        avg_growth_rate = self._calculate_average_growth_rate(vals)
        if avg_growth_rate >= self._score_config.dividend_growth_rate_threshold:
            score += self._score_config.dividend_growth_rate_score

        # 配当トレンドが上向き（Kendall τ > 閾値）
        try:
            tau = self._kendall_tau(vals)
            if tau > self._score_config.dividend_tau_threshold:
                score += self._score_config.dividend_tau_score
        except Exception:
            pass

        return min(score, self._score_config.dividend_max_score)

    def _score_eps(self, eps: List[Any]) -> int:
        """EPS スコアを計算。"""
        score = 0
        raw_vals = [getattr(e, "eps", None) for e in eps]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]

        if len(vals) < 2:
            return 0

        # N年以上EPS増加
        inc_years = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
        if inc_years >= self._score_config.eps_growth_years_threshold:
            score += self._score_config.eps_growth_years_score

        # N年連続EPS増加
        run = 1
        found_run = False
        for i in range(1, len(vals)):
            if vals[i] > vals[i - 1]:
                run += 1
                if run >= self._score_config.eps_consecutive_growth_threshold:
                    found_run = True
            else:
                run = 1

        if found_run:
            score += self._score_config.eps_consecutive_growth_score

        # Kendall τ チェック
        try:
            tau = self._kendall_tau(vals)
            if tau > self._score_config.eps_tau_threshold:
                score += self._score_config.eps_tau_score
        except Exception:
            pass

        return min(score, self._score_config.eps_max_score)

    def _score_stability(self, stabs: List[Any]) -> int:
        """安定性スコアを計算。"""
        score = 0

        raw_sales = [getattr(s, "net_sales", None) for s in stabs]
        raw_incomes = [getattr(s, "operating_income", None) for s in stabs]

        sales: List[float] = [float(v) for v in raw_sales if v is not None]
        incomes: List[float] = [float(v) for v in raw_incomes if v is not None]

        if len(sales) >= 2:
            inc_sales = sum(1 for i in range(1, len(sales)) if sales[i] > sales[i - 1])
            if inc_sales >= self._score_config.stability_sales_growth_threshold:
                score += self._score_config.stability_sales_growth_score

        if len(incomes) >= 2:
            inc_inc = sum(1 for i in range(1, len(incomes)) if incomes[i] > incomes[i - 1])
            if inc_inc >= self._score_config.stability_margin_growth_threshold:
                score += self._score_config.stability_margin_growth_score

        return min(score, self._score_config.stability_max_score)

    def _score_profitability(self, stabs: List[Any]) -> int:
        """収益性スコアを計算。"""
        score = 0

        raw_margins = [getattr(s, "operating_margin", None) for s in stabs]
        margins: List[float] = [float(v) for v in raw_margins if v is not None]

        if len(margins) < 2:
            return 0

        # マージン低下年が閾値以下
        neg_count = sum(1 for i in range(1, len(margins)) if (margins[i] - margins[i - 1]) < 0)
        if neg_count <= self._score_config.profitability_decline_years_threshold:
            score += self._score_config.profitability_decline_score

        # 2.0pt以上の低下が連続していないか
        consec_bad = False
        consec = 0
        for i in range(1, len(margins)):
            if (
                margins[i - 1] - margins[i]
            ) >= self._score_config.profitability_consecutive_decline_threshold:
                consec += 1
                if consec >= 2:
                    consec_bad = True
                    break
            else:
                consec = 0

        if not consec_bad:
            score += self._score_config.profitability_consecutive_decline_score

        return min(score, self._score_config.profitability_max_score)

    # ================ ユーティリティ ================

    def _calculate_average_growth_rate(self, values: List[float]) -> float:
        """過去N年間の平均増配率を計算。"""
        if len(values) < 2:
            return 0.0

        growth_rates = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                rate = (values[i] - values[i - 1]) / values[i - 1]
                growth_rates.append(rate)

        if not growth_rates:
            return 0.0

        return sum(growth_rates) / len(growth_rates)

    def _kendall_tau(self, values: List[float]) -> float:
        """Kendall τ-a を計算（簡略版）。"""
        n = len(values)
        if n < 2:
            return 0.0

        concordant = 0
        discordant = 0

        for i in range(n - 1):
            for j in range(i + 1, n):
                vi, vj = values[i], values[j]
                if vi == vj:
                    continue
                if (vi < vj and i < j) or (vi > vj and i > j):
                    concordant += 1
                else:
                    discordant += 1

        denom = concordant + discordant
        if denom == 0:
            return 0.0

        return (concordant - discordant) / denom

    def _resolve_status(self, pass_required: bool, total_score: int) -> str:
        """ステータスを決定。"""
        if not pass_required:
            return "not_eligible"

        if total_score >= self._score_config.status_priority_threshold:
            return "priority"
        if total_score >= self._score_config.status_active_threshold:
            return "active"
        if total_score >= self._score_config.status_watch_threshold:
            return "watch"

        return "not_eligible"

    @staticmethod
    def _extract_latest_fiscal_year_end(
        divs: List[Any],
        eps: List[Any],
        stabs: List[Any],
    ) -> Optional[date]:
        """最新の決算年度を抽出。"""
        for source in (stabs, divs, eps):
            if source:
                last = source[-1]
                fy = getattr(last, "fiscal_year_end", None)
                if fy is not None:
                    return fy
        return None
