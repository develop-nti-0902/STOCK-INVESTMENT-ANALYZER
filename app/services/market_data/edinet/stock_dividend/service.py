"""EDINET 配当情報サービスの orchestration モジュール."""

from __future__ import annotations

from datetime import date
from typing import Any, List

from app.models.edinet_stock_dividend import EdinetStockDividend
from app.services.market_data.edinet.download_service import EdinetDownloadService
from app.services.market_data.edinet.file_manager import EdinetFileManager
from app.services.market_data.edinet.stock_dividend.converter import EdinetStockDividendConverter
from app.services.market_data.edinet.stock_dividend.parser import EdinetStockDividendParser
from app.services.market_data.edinet.stock_dividend.saver import EdinetStockDividendSaver
from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetStockDividendService:
    """EDINET 配当情報のオーケストレーションサービス."""

    def __init__(
        self,
        parser: EdinetStockDividendParser,
        converter: EdinetStockDividendConverter,
        saver: EdinetStockDividendSaver,
        file_manager: EdinetFileManager,
        download_service: EdinetDownloadService,
    ) -> None:
        """Initialize orchestration service with parser/converter/saver and helpers."""
        self.parser = parser
        self.converter = converter
        self.saver = saver
        self.file_manager = file_manager
        self.download_service = download_service

        parser_callable = getattr(self.parser, "parse_root", getattr(self.parser, "parse", None))
        saver_callable = getattr(self.saver, "save", getattr(self.saver, "save_single", None))
        pairs = []
        if parser_callable is not None and saver_callable is not None:
            pairs.append((parser_callable, self.converter, saver_callable))

        self._aggregate = EdinetAggregateUpdateService(
            download_service=download_service, parser_saver_pairs=pairs
        )

    async def get_latest_data(self, sec_code: str) -> Any:
        """Return the latest stock dividend data for the given security code."""
        return await self.saver.get_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date) -> Any:
        """Return stock dividend data for a specific period."""
        return await self.saver.repository.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int) -> Any:
        """Return stock dividend data for a fiscal year."""
        return await self.saver.repository.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]) -> List[EdinetStockDividend]:
        """Return latest stock dividend records for multiple security codes."""
        return await self.saver.repository.get_latest_by_sec_codes(sec_codes)

    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """Remove old downloaded files via the file manager and return removed count."""
        work_dir = getattr(self.download_service, "work_dir", None)
        if work_dir is None:
            return 0
        return self.file_manager.cleanup_old_files(work_dir, max_age_hours=max_age_hours)


__all__ = ["EdinetStockDividendService"]
