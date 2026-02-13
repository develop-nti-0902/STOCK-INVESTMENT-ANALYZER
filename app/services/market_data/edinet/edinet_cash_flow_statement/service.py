"""EDINET キャッシュフローサービスの orchestration モジュール.

fetcher, parser, converter, saver, file_manager を組み合わせて
文書取得→解析→変換→保存 を行います.
"""

from __future__ import annotations

from datetime import date

from app.services.market_data.edinet.download_service import EdinetDownloadService
from app.services.market_data.edinet.edinet_cash_flow_statement.converter import (
    EdinetCashFlowStatementConverter,
)
from app.services.market_data.edinet.edinet_cash_flow_statement.parser import (
    EdinetCashFlowStatementParser,
)
from app.services.market_data.edinet.edinet_cash_flow_statement.saver import (
    EdinetCashFlowStatementSaver,
)
from app.services.market_data.edinet.file_manager import EdinetFileManager
from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetCashFlowStatementService:
    """EDINET キャッシュフロー計算書のオーケストレーションサービス."""

    def __init__(
        self,
        parser: EdinetCashFlowStatementParser,
        converter: EdinetCashFlowStatementConverter,
        saver: EdinetCashFlowStatementSaver,
        file_manager: EdinetFileManager,
        download_service: EdinetDownloadService,
    ) -> None:
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

    async def get_latest_by_sec_code(self, sec_code: str):
        return await self.saver.repository.find_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date):
        return await self.saver.repository.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int):
        return await self.saver.repository.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]):
        return await self.saver.repository.get_latest_by_sec_codes(sec_codes)


__all__ = ["EdinetCashFlowStatementService"]
