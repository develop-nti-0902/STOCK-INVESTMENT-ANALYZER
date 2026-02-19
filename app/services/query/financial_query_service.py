"""EDINET リポジトリを束ね、スクリーニング用の時系列財務データを返すサービス群を提供するモジュール."""

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, List


@dataclass
class DividendRecord:
    """配当記録を表す dataclass。"""

    fiscal_year_end: date
    dividend_per_share: float


@dataclass
class EpsRecord:
    """EPS 記録を表す dataclass。"""

    fiscal_year_end: date
    eps: float


@dataclass
class CfRecord:
    """営業キャッシュフロー記録を表す dataclass。"""

    fiscal_year_end: date
    operating_cf: float


@dataclass
class StabilityRecord:
    """年度ごとの安定性指標を表す dataclass。"""

    fiscal_year_end: date
    net_sales: float
    operating_income: float
    operating_margin: float


class FinancialQueryService:
    """EDINETリポジトリを束ねてスクリーニング用の時系列財務データを返すサービス。

    コンストラクタでは以下のようなリポジトリオブジェクトを受け取ります:
      - dividend_repo: `list_dividends(sec_code)` を提供
      - profit_and_loss_repo: `list_profit_and_loss(sec_code)` を提供
      - cash_flow_repo: `list_cash_flows(sec_code)` を提供

    リポジトリが返す各レコードは `dict` か属性を持つオブジェクトのいずれかを想定します。
    使用するフィールド:
      - fiscal_year_end (datetime.date)
      - dividend_per_share (float)
      - eps (float)
      - net_sales (float)
      - operating_income (float)
      - operating_cf (float)
    """

    def __init__(self, dividend_repo: Any, profit_and_loss_repo: Any, cash_flow_repo: Any):
        """依存する EDINET リポジトリを受け取りサービスを初期化します."""
        # リポジトリを保持
        self._dividend_repo = dividend_repo
        self._pl_repo = profit_and_loss_repo
        self._cf_repo = cash_flow_repo

    @staticmethod
    def _get_field(item, name):
        # レコードが dict の場合は key から、それ以外は属性参照で値を取り出す
        if item is None:
            return None
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name, None)

    @staticmethod
    def _sort_by_date(records: Iterable[Any], date_field: str) -> List[Any]:
        # 指定した日付フィールドでソート（欠損値は最小日付として扱う）
        return sorted(
            records, key=lambda r: FinancialQueryService._get_field(r, date_field) or date.min
        )

    def _take_last_years(self, sorted_records: List[Any], years: int) -> List[Any]:
        # 最新 N 件を返す（返却順は古いものから）
        if years is None or years <= 0:
            return sorted_records
        last = sorted_records[-years:]
        return last

    def get_dividend_history(self, sec_code: str, years: int = 5) -> List[DividendRecord]:
        """過去 `years` 年分の配当履歴を古い順で返す。

        リポジトリ側メソッド: `list_dividends(sec_code)` を期待する。
        """
        raw: List[Any] = []
        if hasattr(self._dividend_repo, "list_dividends"):
            raw = self._dividend_repo.list_dividends(sec_code) or []
        sorted_records = self._sort_by_date(raw, "fiscal_year_end")
        selected = self._take_last_years(sorted_records, years)
        out: List[DividendRecord] = []
        for r in selected:
            fy = self._get_field(r, "fiscal_year_end")
            dps = self._get_field(r, "dividend_per_share")
            if fy is None:
                continue
            out.append(
                DividendRecord(
                    fiscal_year_end=fy, dividend_per_share=float(dps) if dps is not None else 0.0
                )
            )
        return out

    def get_eps_history(self, sec_code: str, years: int = 5) -> List[EpsRecord]:
        """過去 `years` 年分の EPS 履歴を古い順で返す。

        リポジトリ側メソッド: `list_profit_and_loss(sec_code)` を期待する。
        """
        raw: List[Any] = []
        if hasattr(self._pl_repo, "list_profit_and_loss"):
            raw = self._pl_repo.list_profit_and_loss(sec_code) or []
        sorted_records = self._sort_by_date(raw, "fiscal_year_end")
        selected = self._take_last_years(sorted_records, years)
        out: List[EpsRecord] = []
        for r in selected:
            fy = self._get_field(r, "fiscal_year_end")
            eps = self._get_field(r, "eps")
            if fy is None:
                continue
            out.append(EpsRecord(fiscal_year_end=fy, eps=float(eps) if eps is not None else 0.0))
        return out

    def get_operating_cf_history(self, sec_code: str, years: int = 5) -> List[CfRecord]:
        """過去 `years` 年分の営業キャッシュフローを古い順で返す。

        リポジトリ側メソッド: `list_cash_flows(sec_code)` を期待する。
        """
        raw: List[Any] = []
        if hasattr(self._cf_repo, "list_cash_flows"):
            raw = self._cf_repo.list_cash_flows(sec_code) or []
        sorted_records = self._sort_by_date(raw, "fiscal_year_end")
        selected = self._take_last_years(sorted_records, years)
        out: List[CfRecord] = []
        for r in selected:
            fy = self._get_field(r, "fiscal_year_end")
            ocf = self._get_field(r, "operating_cf")
            if fy is None:
                continue
            out.append(
                CfRecord(fiscal_year_end=fy, operating_cf=float(ocf) if ocf is not None else 0.0)
            )
        return out

    def get_stability_history(self, sec_code: str, years: int = 5) -> List[StabilityRecord]:
        """過去 `years` 年分の売上・営業利益・営業利益率を古い順で返す。

        リポジトリ側メソッド: `list_profit_and_loss(sec_code)` を期待する。
        """
        raw: List[Any] = []
        if hasattr(self._pl_repo, "list_profit_and_loss"):
            raw = self._pl_repo.list_profit_and_loss(sec_code) or []
        sorted_records = self._sort_by_date(raw, "fiscal_year_end")
        selected = self._take_last_years(sorted_records, years)
        out: List[StabilityRecord] = []
        for r in selected:
            fy = self._get_field(r, "fiscal_year_end")
            net_sales = self._get_field(r, "net_sales")
            op_income = self._get_field(r, "operating_income")
            if fy is None:
                continue
            ns = float(net_sales) if net_sales is not None else 0.0
            oi = float(op_income) if op_income is not None else 0.0
            margin = (oi / ns) if ns != 0 else 0.0
            out.append(
                StabilityRecord(
                    fiscal_year_end=fy, net_sales=ns, operating_income=oi, operating_margin=margin
                )
            )
        return out
