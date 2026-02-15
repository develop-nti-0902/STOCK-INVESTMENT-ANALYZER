"""EDINET キャッシュフロー計算書データ Saver.

EdinetCashFlowStatementRepository を使用してデータベースへの保存を行います。
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.edinet.edinet_cash_flow_statement_repository import (
    EdinetCashFlowStatementRepository,
)
from app.services.core.savers.base_saver import BaseSaver
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetCashFlowStatementSaver(BaseSaver[Dict[str, Any]]):
    """EDINET キャッシュフロー計算書データ Saver."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize saver with DB session and repository."""
        super().__init__()
        self.session = session
        self.repository = EdinetCashFlowStatementRepository(session)

    async def save_single(self, data: Dict[str, Any]) -> Any:
        """Save a single record using the repository upsert."""
        return await self.repository.upsert(data)

    async def save(self, data: Dict[str, Any], **kwargs: Any) -> Any:
        """Save a single record (alias for save_single)."""
        return await self.save_single(data)

    async def save_batch(self, data_list: List[Dict[str, Any]], **kwargs: Any) -> int:
        """Save multiple records, returning number saved.

        Raises on unexpected errors after logging.
        """
        saved_count = 0
        for data in data_list:
            try:
                await self.repository.upsert(data)
                saved_count += 1
            except Exception as e:
                logger.exception("Failed to save record: %s", e)
                raise
        return saved_count

    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate minimum required fields exist in the record dict."""
        required_fields = [
            "doc_id",
            "sec_code",
            "submission_date",
            "period_end_date",
            "report_type",
        ]
        for field in required_fields:
            if field not in data:
                logger.warning("Missing required field: %s", field)
                return False
        return True


__all__ = ["EdinetCashFlowStatementSaver"]
