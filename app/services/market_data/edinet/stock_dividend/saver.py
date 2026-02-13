"""EDINET 配当データ Saver.

EdinetStockDividendRepository を使って DB 保存を行います。
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.edinet_stock_dividend_repository import EdinetStockDividendRepository
from app.services.core.savers.base_saver import BaseSaver
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetStockDividendSaver(BaseSaver[Dict[str, Any]]):
    """EDINET 配当データの Saver."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize saver with DB session and repository."""
        super().__init__()
        self.session = session
        self.repository = EdinetStockDividendRepository(session)

    async def save_single(self, data: Dict[str, Any]) -> Any:
        """Validate and upsert a single stock dividend record."""
        if not data:
            raise ValueError("data is required")

        required_fields = ["sec_code", "period_end_date"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field '{field}' is missing")

        logger.debug(f"Upserting stock dividend data for {data.get('sec_code')}")
        result = await self.repository.upsert(data)
        logger.info(f"Successfully upserted stock dividend data: {getattr(result, 'id', None)}")
        return result

    async def save_batch(self, data_list: List[Dict[str, Any]], **kwargs: Any) -> Any:
        """Save multiple records, returning list of results for successful saves."""
        results = []
        for data in data_list:
            try:
                result = await self.save_single(data)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to save record: {data}. Error: {e}")
                continue
        logger.info(f"Batch save completed. {len(results)} of {len(data_list)} records saved.")
        return results

    async def save(self, data: Dict[str, Any], **kwargs: Any) -> Any:
        """Save a single record (alias of save_single)."""
        return await self.save_single(data)

    async def exists(self, sec_code: str, period_end_date: Any) -> bool:
        """Return True if a record exists for given security code and period."""
        result = await self.repository.find_by_period(sec_code, period_end_date)
        return result is not None

    async def get_latest_by_sec_code(self, sec_code: str) -> Any:
        """Return latest stock dividend record for the security code."""
        return await self.repository.find_latest_by_sec_code(sec_code)

    def validate_data_sync(self, data: Dict[str, Any]) -> bool:
        """Synchronous validation used in non-async contexts.

        Checks that required keys are present and not None.
        """
        if not isinstance(data, dict):
            return False
        required_fields = ["sec_code", "period_end_date"]
        return all(field in data and data[field] is not None for field in required_fields)


__all__ = ["EdinetStockDividendSaver"]
