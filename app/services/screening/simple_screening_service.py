"""シンプルなスクリーニングサービスを実装するモジュール。"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.market_data.stock_master import (
    StockCodeMappingRepository,
    StockMasterRepository,
)
from app.repositories.screening.screening_result_repository import ScreeningResultRepository
from app.services.data_synchronization.market_data.stock_master.service import StockMasterService
from app.utils.stock_code_converter import to_edinet_code

logger = logging.getLogger(__name__)


@dataclass
# pylint: disable=too-many-instance-attributes
class ScreeningResult:
    """単一銘柄のスクリーニング結果を表す dataclass。"""

    sec_code: str
    pass_required: bool
    total_score: int
    score_dividend: int
    score_eps: int
    score_stability: int
    score_profitability: int
    status: str
    failed_conditions: List[str]
    fiscal_year_end: Optional[date]


class SimpleScreeningService:
    """Issue 2 のロジックを実装したシンプルなスクリーニングサービス。

    コンストラクタで `FinancialQueryService` 相当のオブジェクトと非同期セッションメーカーを受け取ります。
    設計書通りに `get_*_history` メソッドを利用し、結果を逐次的に出力します。
    """

    def __init__(
        self,
        financial_query_service: Any,
        stock_master_maker: Optional[async_sessionmaker[AsyncSession]] = None,
        screening_result_maker: Optional[async_sessionmaker[AsyncSession]] = None,
        screening_result_factory: Callable[
            [AsyncSession], ScreeningResultRepository
        ] = ScreeningResultRepository,
    ):
        """`FinancialQueryService` と必要なセッションメーカー／リポジトリを受け取り初期化します."""
        self._fq = financial_query_service
        self._stock_master_maker = stock_master_maker
        self._screening_result_maker = screening_result_maker
        self._screening_result_factory = screening_result_factory

    async def _async_fetch_all_stock_master_codes(self) -> List[str]:
        maker = self._stock_master_maker
        if maker is None:
            raise RuntimeError("stock_master_maker is required to fetch all codes")
        try:
            async with maker() as session:
                repo = StockMasterRepository(session=session)
                sm_service = StockMasterService(repo=repo)
                symbols = await sm_service.get_all_active_symbols()
                out: List[str] = []
                mapping_repo = StockCodeMappingRepository(session=session)
                for c in symbols:
                    try:
                        # stock_code_mapping テーブルから対応する sec_code を取得
                        mapping = await mapping_repo.get_by_stock_code(c)
                        if mapping:
                            out.append(mapping.sec_code)
                        else:
                            # フォールバック: 対応がない場合は静的変換を使用
                            out.append(to_edinet_code(c))
                    except Exception as e:
                        print(f"[DEBUG] failed convert code {c}: {e}")
                return out
        except Exception as exc:
            print(f"[DEBUG] fetch stock master failed: {exc}")
            return []

    async def run(self, sec_codes: Optional[List[str]], evaluation_date: date) -> None:
        """与えられた銘柄リスト（または None）でスクリーニングを実行し結果を標準出力します.

        Args:
            sec_codes: 対象銘柄コードのリスト。None の場合は銘柄マスターから全銘柄を取得します。
            evaluation_date: 評価実行日
        """
        if sec_codes is None:
            sec_codes = await self._async_fetch_all_stock_master_codes()

        print(f"[{evaluation_date}] スクリーニング結果（逐次出力）")
        passed_count = 0
        failed_count = 0
        total = len(sec_codes)
        passed_summaries: List[str] = []
        for code in sec_codes:
            res = await self.evaluate(code, evaluation_date)
            await self._persist_result(res, evaluation_date)
            score_part = f"{res.sec_code}: スコア{res.total_score} ({res.status})"
            details = (
                f"配当{res.score_dividend}/EPS{res.score_eps} "
                f"安定{res.score_stability}/収益{res.score_profitability}"
            )
            summary = f"{score_part} - {details}"
            if res.status in ("priority", "active", "watch"):
                passed_count += 1
                print(f"通過: {summary}")
                passed_summaries.append(summary)
            else:
                failed_count += 1
                failed_info = ",".join(res.failed_conditions) or "なし"
                print(f"不合格: {summary} failed_conditions=[{failed_info}]")
        print(f"--- 合格 {passed_count}件 / 不合格 {failed_count}件 / 全体 {total}件 ---")
        if passed_summaries:
            print("--- 合格対象一覧 ---")
            for line in passed_summaries:
                print(f"  {line}")
        else:
            print("--- 合格対象はありませんでした ---")

    async def evaluate(self, sec_code: str, _evaluation_date: date) -> ScreeningResult:
        """単一銘柄についてスクリーニングを行い `ScreeningResult` を返します."""
        # 履歴データを取得（古い順 -> 新しい順）
        divs = list(await self._call_history("get_dividend_history", sec_code) or [])
        eps = list(await self._call_history("get_eps_history", sec_code) or [])
        cfs = list(await self._call_history("get_operating_cf_history", sec_code) or [])
        stabs = list(await self._call_history("get_stability_history", sec_code) or [])

        failed: List[str] = []

        # 必須条件チェック
        if not self._check_dividend_continuity(divs):
            failed.append("dividend_continuity")
        if not self._check_eps_health(eps):
            failed.append("eps_health")
        if not self._check_operating_cf(cfs):
            failed.append("operating_cf")

        pass_required = len(failed) == 0

        # Scoring
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

    async def _call_history(self, method_name: str, sec_code: str) -> Any:
        method = getattr(self._fq, method_name)
        result = method(sec_code, years=5)
        if inspect.isawaitable(result):
            return await result
        return result

    # ----------------- 必須条件チェック -----------------
    def _check_dividend_continuity(self, divs: List[Any]) -> bool:
        if not divs:
            return False
        raw_vals = [getattr(d, "dividend_per_share", None) for d in divs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        if len(vals) < 2:
            return False

        # 過去5年間において減配していないことを確認
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                return False

        # 過去5年間において3年以上連続増配（または現状維持）の期間が存在
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

        return max_consecutive_increase >= 3

    def _check_eps_health(self, eps: List[Any]) -> bool:
        if not eps:
            return False
        raw_vals = [getattr(e, "eps", None) for e in eps]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        # EPS が負またはゼロでないこと
        if any(v <= 0 for v in vals):
            return False
        # 直近2年で連続して減少していないことを確認
        dec_flags = []
        for i in range(1, len(vals)):
            dec_flags.append(vals[i] < vals[i - 1])
        if len(dec_flags) >= 2 and dec_flags[-1] and dec_flags[-2]:
            return False
        # 過去5年間において、減少している年度がある場合、減少率が30%未満であること
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                decrease_rate = (vals[i - 1] - vals[i]) / vals[i - 1]
                if decrease_rate >= 0.3:
                    return False
        return True

    def _check_operating_cf(self, cfs: List[Any]) -> bool:
        if not cfs:
            return False
        raw_vals = [getattr(c, "operating_cf", None) for c in cfs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        positive_years = sum(1 for v in vals if v > 0)
        # 過去5年で営業CFがプラスの年が4年以上あること
        return positive_years >= 4

    # ----------------- スコア計算 -----------------
    def _score_dividend(self, divs: List[Any]) -> int:
        score = 0
        raw_vals = [getattr(d, "dividend_per_share", None) for d in divs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        if len(vals) < 2:
            return 0

        # 過去5年間連続増配（またはそれ以上、現状維持を含む）
        all_increasing = all(vals[i] >= vals[i - 1] for i in range(1, len(vals)))
        if all_increasing:
            score += 10

        # 過去5年間平均増配率が5%以上
        avg_growth_rate = self._calculate_average_growth_rate(vals)
        if avg_growth_rate >= 0.05:
            score += 10

        # 5年配当トレンドが上向き（Kendallのτ > 0.4）
        try:
            tau = self._kendall_tau(vals)
            if tau > 0.4:
                score += 10
        except Exception:
            pass
        return min(score, 30)

    def _score_eps(self, eps: List[Any]) -> int:
        score = 0
        raw_vals = [getattr(e, "eps", None) for e in eps]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        if len(vals) < 2:
            return 0
        inc_years = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
        if inc_years >= 3:
            score += 10
        # 3年以上連続でEPS増加
        run = 1
        found_run = False
        for i in range(1, len(vals)):
            if vals[i] > vals[i - 1]:
                run += 1
                if run >= 3:
                    found_run = True
            else:
                run = 1
        if found_run:
            score += 10
        try:
            tau = self._kendall_tau(vals)
            if tau > 0.4:
                score += 10
        except Exception:
            pass
        return min(score, 30)

    def _score_stability(self, stabs: List[Any]) -> int:
        score = 0
        raw_sales = [getattr(s, "net_sales", None) for s in stabs]
        raw_incomes = [getattr(s, "operating_income", None) for s in stabs]
        sales: List[float] = [float(v) for v in raw_sales if v is not None]
        incomes: List[float] = [float(v) for v in raw_incomes if v is not None]
        if len(sales) >= 2:
            # 売上増加年が3年以上あるか
            inc_sales = sum(1 for i in range(1, len(sales)) if sales[i] > sales[i - 1])
            if inc_sales >= 3:
                score += 10
        if len(incomes) >= 2:
            # 営業利益の増加年が3年以上あるか
            inc_inc = sum(1 for i in range(1, len(incomes)) if incomes[i] > incomes[i - 1])
            if inc_inc >= 3:
                score += 10
        return min(score, 20)

    def _score_profitability(self, stabs: List[Any]) -> int:
        score = 0
        raw_margins = [getattr(s, "operating_margin", None) for s in stabs]
        margins: List[float] = [float(v) for v in raw_margins if v is not None]
        if len(margins) < 2:
            return 0
        # 前年差がマイナスになっている年数
        neg_count = sum(1 for i in range(1, len(margins)) if (margins[i] - margins[i - 1]) < 0)
        if neg_count <= 2:
            score += 10
        # 2.0pt以上の低下が2年連続していないかをチェック
        consec_bad = False
        consec = 0
        for i in range(1, len(margins)):
            if (margins[i - 1] - margins[i]) >= 2.0:
                consec += 1
                if consec >= 2:
                    consec_bad = True
                    break
            else:
                consec = 0
        if not consec_bad:
            score += 10
        return min(score, 20)

    # ----------------- Utilities -----------------
    def _calculate_average_growth_rate(self, values: List[float]) -> float:
        """過去5年間の平均増配率を計算する。

        Args:
            values: 古い順から新しい順の配当値のリスト

        Returns:
            平均増配率（例: 0.05 = 5%）
        """
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
        # 単純な Kendall τ-a の実装（タイの扱い等の詳細処理は簡略化）
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
        if not pass_required:
            return "not_eligible"
        if total_score >= 90:
            return "priority"
        if total_score >= 80:
            return "active"
        if total_score >= 70:
            return "watch"
        return "not_eligible"

    async def _persist_result(self, result: ScreeningResult, evaluation_date: date) -> None:
        maker = self._screening_result_maker
        if maker is None:
            return
        payload = self._build_upsert_payload(result, evaluation_date)
        try:
            async with maker.begin() as session:
                repo = self._screening_result_factory(session)
                await repo.upsert(payload)
        except Exception:  # pragma: no cover - best effort persistence
            logger.exception("Failed to persist screening result for %s", result.sec_code)

    def _build_upsert_payload(
        self, result: ScreeningResult, evaluation_date: date
    ) -> Dict[str, Any]:
        return {
            "sec_code": result.sec_code,
            "evaluation_date": evaluation_date,
            "fiscal_year_end": result.fiscal_year_end,
            "pass_required_conditions": result.pass_required,
            "total_score": result.total_score,
            "score_dividend": result.score_dividend,
            "score_eps": result.score_eps,
            "score_stability": result.score_stability,
            "score_profitability": result.score_profitability,
            "status": result.status,
            "failed_conditions": result.failed_conditions or [],
            "screening_details": self._build_screening_details(result),
        }

    @staticmethod
    def _build_screening_details(result: ScreeningResult) -> Dict[str, Any]:
        return {
            "score_breakdown": {
                "dividend": result.score_dividend,
                "eps": result.score_eps,
                "stability": result.score_stability,
                "profitability": result.score_profitability,
            },
            "status": result.status,
            "pass_required": result.pass_required,
            "failed_conditions": result.failed_conditions or [],
            "fiscal_year_end": (
                result.fiscal_year_end.isoformat() if result.fiscal_year_end is not None else None
            ),
        }

    @staticmethod
    def _extract_latest_fiscal_year_end(
        divs: List[Any],
        eps: List[Any],
        stabs: List[Any],
    ) -> Optional[date]:
        for source in (stabs, divs, eps):
            if source:
                last = source[-1]
                fy = getattr(last, "fiscal_year_end", None)
                if fy is not None:
                    return fy
        return None
