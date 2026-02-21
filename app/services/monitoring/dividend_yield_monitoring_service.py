"""配当利回り監視のコアロジックを提供するサービスモジュール."""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.screening.screening_result import ScreeningResult
from app.repositories.market_data.edinet.edinet_stock_dividend_repository import (
    EdinetStockDividendRepository,
)
from app.repositories.market_data.stock_price.stock_data_repository import StockData1dRepository
from app.repositories.monitoring.dividend_yield_monitoring_repository import (
    DividendYieldMonitoringRepository,
)
from app.utils.stock_code_converter import from_edinet_code

logger = logging.getLogger(__name__)

EdinetRepoFactory = Callable[[AsyncSession], EdinetStockDividendRepository]
StockRepoFactory = Callable[[AsyncSession], StockData1dRepository]
MonitoringRepoFactory = Callable[[AsyncSession], DividendYieldMonitoringRepository]

_PURCHASE_LEVEL_ORDER = ["priority", "consider", "watch", "monitor"]
_PURCHASE_LEVEL_LABELS = {
    "priority": "優先購入候補（利回り ≥ 4.0%）:",
    "consider": "購入検討（利回り ≥ 3.5%）:",
    "watch": "監視強化（利回り ≥ 3.0%）:",
    "monitor": "監視継続（利回り < 3.0%）:",
}
_MONITORING_STATUSES = ("watch", "active", "priority")


@dataclass
class DividendYieldMonitoringResult:
    sec_code: str
    dividend_amount: Optional[Decimal]
    stock_price: Optional[Decimal]
    dividend_yield: Optional[Decimal]
    purchase_level: str
    screening_status: str
    screening_score: Optional[int]
    stock_price_date: Optional[date]
    dividend_fiscal_year_end: Optional[date]
    error_message: Optional[str] = None


class DividendYieldMonitoringService:  # pylint: disable=too-many-instance-attributes
    """監視対象銘柄の配当利回りを算出して出力するサービスクラス."""

    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        edinet_repo_factory: EdinetRepoFactory = EdinetStockDividendRepository,
        stock_repo_factory: StockRepoFactory = StockData1dRepository,
        monitoring_repo_factory: MonitoringRepoFactory = DividendYieldMonitoringRepository,
    ):
        self._session_maker = session_maker
        self._edinet_repo_factory = edinet_repo_factory
        self._stock_repo_factory = stock_repo_factory
        self._monitoring_repo_factory = monitoring_repo_factory
        self._screening_index: Dict[str, ScreeningResult] = {}

    async def run(self, monitoring_date: date) -> None:
        screening_results = await self._fetch_screening_results()
        self._screening_index = {result.sec_code: result for result in screening_results}
        monitoring_results: List[DividendYieldMonitoringResult] = []
        for result in screening_results:
            try:
                monitoring_results.append(
                    await self.calculate_for_stock(result.sec_code, monitoring_date)
                )
            except Exception:  # pragma: no cover - best effort per銘柄
                logger.exception("Failed to process dividend yield for %s", result.sec_code)
                monitoring_results.append(
                    DividendYieldMonitoringResult(
                        sec_code=result.sec_code,
                        dividend_amount=None,
                        stock_price=None,
                        dividend_yield=None,
                        purchase_level="unavailable",
                        screening_status=result.status,
                        screening_score=result.total_score,
                        stock_price_date=None,
                        dividend_fiscal_year_end=result.fiscal_year_end,
                        error_message="処理中にエラーが発生しました",
                    )
                )
        await self._persist_monitoring_results(monitoring_date, monitoring_results)
        self._screening_index.clear()
        self._print_report(monitoring_date, monitoring_results)

    async def calculate_for_stock(
        self, sec_code: str, monitoring_date: date
    ) -> DividendYieldMonitoringResult:
        screening_result = self._screening_index.get(sec_code)
        if screening_result is None:
            raise RuntimeError(f"screening result is not ready for {sec_code}")
        logger.debug(
            "Calculating dividend yield for %s (monitoring_date=%s)", sec_code, monitoring_date
        )

        dividend_entry = await self._safe_get_latest_dividend(sec_code)
        dividend_amount = self._extract_dividend_amount(dividend_entry)
        dividend_fiscal_year_end = (
            dividend_entry.period_end_date if dividend_entry is not None else None
        )

        stock_price = None
        stock_price_date: Optional[date] = None
        stock_symbol = self._resolve_stock_symbol(sec_code)
        stock_entry = (
            await self._safe_get_latest_stock_price(stock_symbol) if stock_symbol else None
        )
        if stock_entry is not None:
            stock_price = stock_entry.close
            stock_price_date = stock_entry.timestamp.date()

        dividend_yield = self._calculate_dividend_yield(dividend_amount, stock_price)
        purchase_level = self._resolve_purchase_level(dividend_yield)
        error_message = None
        if purchase_level == "unavailable":
            error_message = self._derive_unavailable_reason(dividend_amount, stock_price)

        return DividendYieldMonitoringResult(
            sec_code=sec_code,
            dividend_amount=dividend_amount,
            stock_price=stock_price,
            dividend_yield=dividend_yield,
            purchase_level=purchase_level,
            screening_status=screening_result.status,
            screening_score=screening_result.total_score,
            stock_price_date=stock_price_date,
            dividend_fiscal_year_end=dividend_fiscal_year_end,
            error_message=error_message,
        )

    async def _safe_get_latest_dividend(self, sec_code: str):
        try:
            async with self._session_maker() as session:
                repo = self._edinet_repo_factory(session)
                return await repo.find_latest_by_sec_code(sec_code)
        except Exception:
            logger.exception("Failed to fetch latest dividend for %s", sec_code)
            return None

    async def _safe_get_latest_stock_price(self, symbol: str):
        try:
            async with self._session_maker() as session:
                repo = self._stock_repo_factory(session)
                records = await repo.get_latest(symbol)
                return records[0] if records else None
        except Exception:
            logger.exception("Failed to fetch latest stock price for %s", symbol)
            return None

    async def _fetch_screening_results(self) -> List[ScreeningResult]:
        async with self._session_maker() as session:
            stmt = (
                select(ScreeningResult)
                .where(ScreeningResult.status.in_(_MONITORING_STATUSES))
                .order_by(ScreeningResult.sec_code, desc(ScreeningResult.evaluation_date))
            )
            result = await session.execute(stmt)
            latest: Dict[str, ScreeningResult] = {}
            for record in result.scalars():
                if record.sec_code not in latest:
                    latest[record.sec_code] = record
            return list(latest.values())

    @staticmethod
    def _extract_dividend_amount(entry) -> Optional[Decimal]:
        if entry is None or entry.dividend_actual is None:
            return None
        value = entry.dividend_actual
        return Decimal(str(value)) if not isinstance(value, Decimal) else value

    @staticmethod
    def _calculate_dividend_yield(
        dividend_amount: Optional[Decimal], stock_price: Optional[Decimal]
    ) -> Optional[Decimal]:
        if dividend_amount is None or stock_price is None:
            return None
        if dividend_amount <= 0 or stock_price <= 0:
            return None
        return (dividend_amount / stock_price) * Decimal("100")

    @staticmethod
    def _resolve_purchase_level(dividend_yield: Optional[Decimal]) -> str:
        if dividend_yield is None:
            return "unavailable"
        if dividend_yield >= Decimal("4.0"):
            return "priority"
        if dividend_yield >= Decimal("3.5"):
            return "consider"
        if dividend_yield >= Decimal("3.0"):
            return "watch"
        return "monitor"

    def _derive_unavailable_reason(
        self, dividend_amount: Optional[Decimal], stock_price: Optional[Decimal]
    ) -> str:
        if dividend_amount is None:
            return "配当データなし"
        if dividend_amount <= Decimal("0"):
            return "配当金が0以下"
        if stock_price is None:
            return "株価データなし"
        if stock_price <= Decimal("0"):
            return "株価が0以下"
        return "利回り計算不可"

    @staticmethod
    def _resolve_stock_symbol(sec_code: str) -> Optional[str]:
        try:
            symbol = from_edinet_code(sec_code)
            return symbol
        except Exception:
            logger.exception("Failed to normalize sec_code=%s for stock lookup", sec_code)
            return None

    def _print_report(
        self, monitoring_date: date, results: List[DividendYieldMonitoringResult]
    ) -> None:
        header = "=" * 36
        print(f"[{monitoring_date.isoformat()}] 配当利回り監視結果")
        print(header)
        grouped = self._group_results(results)
        for level in _PURCHASE_LEVEL_ORDER:
            entries = grouped.get(level, [])
            if not entries:
                continue
            print(_PURCHASE_LEVEL_LABELS[level])
            for entry in sorted(
                entries,
                key=lambda r: (
                    r.dividend_yield if r.dividend_yield is not None else Decimal("0"),
                    r.screening_score if r.screening_score is not None else 0,
                ),
                reverse=True,
            ):
                print(self._format_result_line(entry))
        unavailable = grouped.get("unavailable", [])
        if unavailable:
            print("データ取得不可:")
            for entry in unavailable:
                reason = entry.error_message or self._derive_unavailable_reason(
                    entry.dividend_amount, entry.stock_price
                )
                print(f"  {entry.sec_code}: {reason}")
        print(header)
        print(
            f"合計監視対象: {len(results)}銘柄 / "
            f"優先購入候補: {len(grouped.get('priority', []))}銘柄 / "
            f"購入検討: {len(grouped.get('consider', []))}銘柄"
        )

    @staticmethod
    def _format_result_line(result: DividendYieldMonitoringResult) -> str:
        score = result.screening_score if result.screening_score is not None else "N/A"
        percentage = DividendYieldMonitoringService._format_percentage(result.dividend_yield)
        stock_value = DividendYieldMonitoringService._format_currency(result.stock_price)
        dividend_value = DividendYieldMonitoringService._format_currency(result.dividend_amount)
        status = f"[{result.screening_status}/{score}]"
        return (
            f"  {result.sec_code}: 利回り {percentage} "
            f"(stock: {stock_value}, "
            f"dividend: {dividend_value}) "
            f"{status}"
        )

    @staticmethod
    def _format_currency(value: Optional[Decimal]) -> str:
        if value is None:
            return "N/A"
        return f"¥{value:,.0f}"

    @staticmethod
    def _format_percentage(value: Optional[Decimal]) -> str:
        if value is None:
            return "N/A"
        rounded = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"{rounded:.1f}%"

    @staticmethod
    def _group_results(
        results: List[DividendYieldMonitoringResult],
    ) -> Dict[str, List[DividendYieldMonitoringResult]]:
        groups: Dict[str, List[DividendYieldMonitoringResult]] = {
            level: [] for level in _PURCHASE_LEVEL_ORDER
        }
        groups["unavailable"] = []
        for result in results:
            if result.purchase_level in groups:
                groups[result.purchase_level].append(result)
            else:
                groups["unavailable"].append(result)
        return groups

    async def _persist_monitoring_results(
        self, monitoring_date: date, results: List[DividendYieldMonitoringResult]
    ) -> None:
        if not results:
            return

        payloads = self._build_persistence_payload(monitoring_date, results)
        try:
            async with self._session_maker() as session:
                repository = self._monitoring_repo_factory(session)
                async with session.begin():
                    saved_rows = await repository.bulk_upsert(payloads)
                logger.info(
                    "Persisted %s dividend yield monitoring rows for %s",
                    saved_rows,
                    monitoring_date,
                )
        except Exception:
            logger.exception("Failed to persist dividend yield monitoring results")

    @staticmethod
    def _build_persistence_payload(
        monitoring_date: date, results: List[DividendYieldMonitoringResult]
    ) -> List[dict]:
        return [
            {
                "sec_code": result.sec_code,
                "monitoring_date": monitoring_date,
                "latest_dividend_amount": result.dividend_amount,
                "latest_stock_price": result.stock_price,
                "dividend_yield": result.dividend_yield,
                "purchase_level": result.purchase_level,
                "screening_status": result.screening_status,
                "screening_total_score": result.screening_score,
                "stock_price_source_date": result.stock_price_date,
                "dividend_source_date": result.dividend_fiscal_year_end,
            }
            for result in results
        ]


__all__ = ["DividendYieldMonitoringResult", "DividendYieldMonitoringService"]
