from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, List


@dataclass
# pylint: disable=too-many-instance-attributes
class ScreeningResult:
    sec_code: str
    pass_required: bool
    total_score: int
    score_dividend: int
    score_eps: int
    score_stability: int
    score_profitability: int
    status: str
    failed_conditions: List[str]


class SimpleScreeningService:
    """Issue 2 のロジックを実装したシンプルなスクリーニングサービス。

    コンストラクタで `FinancialQueryService` に相当するオブジェクトを受け取り、
    以下のメソッドを利用します:
      - get_dividend_history(sec_code, years=5)
      - get_eps_history(sec_code, years=5)
      - get_operating_cf_history(sec_code, years=5)
      - get_stability_history(sec_code, years=5)

    返却されるレコードは古い順（old->new）で、設計書に示した数値属性を持つことが前提です。
    """

    def __init__(self, financial_query_service: Any):
        self._fq = financial_query_service

    def run(self, sec_codes: List[str], evaluation_date: date) -> None:
        passed: List[ScreeningResult] = []
        failed: List[ScreeningResult] = []
        for code in sec_codes:
            res = self.evaluate(code, evaluation_date)
            if res.status in ("priority", "active", "watch"):
                passed.append(res)
            else:
                failed.append(res)

        print(f"[{evaluation_date}] スクリーニング結果")
        if passed:
            codes = ", ".join(r.sec_code for r in passed)
            print(f"通過銘柄: {codes}")
        else:
            print("通過銘柄: なし")
        print("---")
        for r in passed:
            part1 = f"{r.sec_code}: スコア{r.total_score} ({r.status}) -"
            part2 = f"配当{r.score_dividend}/EPS{r.score_eps}"
            part3 = f"安定{r.score_stability}/収益{r.score_profitability}"
            details = " ".join([part1, part2, part3])
            print(details)
        if failed:
            bad_list = [f"{r.sec_code} ({','.join(r.failed_conditions)})" for r in failed]
            bad = ", ".join(bad_list)
            print(f"不合格: {bad}")

    def evaluate(self, sec_code: str, _evaluation_date: date) -> ScreeningResult:
        # 履歴データを取得（古い順 -> 新しい順）
        divs = list(self._fq.get_dividend_history(sec_code, years=5) or [])
        eps = list(self._fq.get_eps_history(sec_code, years=5) or [])
        cfs = list(self._fq.get_operating_cf_history(sec_code, years=5) or [])
        stabs = list(self._fq.get_stability_history(sec_code, years=5) or [])

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
        )

    # ----------------- 必須条件チェック -----------------
    def _check_dividend_continuity(self, divs: List[Any]) -> bool:
        if not divs:
            return False
        # 連年での配当減少を数える
        dec_count = 0
        dec_flags = []
        raw_vals = [getattr(d, "dividend_per_share", None) for d in divs]
        vals: List[float] = [float(v) for v in raw_vals if v is not None]
        for i in range(1, len(vals)):
            if vals[i] < vals[i - 1]:
                dec_count += 1
                dec_flags.append(True)
            else:
                dec_flags.append(False)
        # 全体で減配は最大2回まで許容
        if dec_count > 2:
            return False
        # 直近2年で連続減配が発生していないかチェック
        if len(dec_flags) >= 2 and dec_flags[-1] and dec_flags[-2]:
            return False
        return True

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
        # 直近1年の減少率が30%未満であること
        if len(vals) >= 2:
            prev, last = vals[-2], vals[-1]
            if prev > 0 and (prev - last) / prev >= 0.3:
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
        # 増配している年数
        inc_years = sum(1 for i in range(1, len(vals)) if vals[i] > vals[i - 1])
        if inc_years >= 3:
            score += 10
        # 連続増配が2年以上あるか
        run = 1
        found_run = False
        for i in range(1, len(vals)):
            if vals[i] > vals[i - 1]:
                run += 1
                if run >= 2:
                    found_run = True
            else:
                run = 1
        if found_run:
            score += 10
        # Kendall τ による上昇トレンド判定
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
        # 連続増加の判定
        run = 1
        found_run = False
        for i in range(1, len(vals)):
            if vals[i] > vals[i - 1]:
                run += 1
                if run >= 2:
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
