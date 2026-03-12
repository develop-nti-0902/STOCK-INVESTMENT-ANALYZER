"""Dividend yield monitoring repository implementation."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, List

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import DividendYieldMonitoring
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)


class DividendYieldMonitoringRepository(BaseRepository[DividendYieldMonitoring]):
    """Repository to manage DividendYieldMonitoring records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=DividendYieldMonitoring)

    async def bulk_upsert(self, records: List[dict[str, Any]]) -> int:
        """Upsert a batch of monitoring rows by sec_code and monitoring_date."""
        if not records:
            return 0

        table = self.model.__table__
        stmt = insert(table).values(records)
        update_dict = {
            column.name: getattr(stmt.excluded, column.name)
            for column in table.c
            if column.name not in ("id", "created_at")
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["sec_code", "monitoring_date"],
            set_=update_dict,
        )

        try:
            result = await self.session.execute(stmt)
            rowcount = getattr(result, "rowcount", None)
            return rowcount or len(records)
        except Exception:
            logger.exception("Failed to upsert dividend yield monitoring records")
            raise

    async def delete_by_date(self, monitoring_date: date) -> int:
        """Remove monitoring rows for the provided monitoring date."""
        table = self.model.__table__
        stmt = delete(table).where(table.c.monitoring_date == monitoring_date)
        try:
            result = await self.session.execute(stmt)
            rowcount = getattr(result, "rowcount", None)
            return rowcount or 0
        except Exception:
            logger.exception(
                "Failed to delete dividend yield monitoring records for %s", monitoring_date
            )
            raise


__all__ = ["DividendYieldMonitoringRepository"]
