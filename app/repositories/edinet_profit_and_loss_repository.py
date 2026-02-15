"""edinet_profit_and_loss テーブル用 Repository 実装.

新しいモデル定義に合わせて実装を一新しています。互換性は保持しません。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from app.models.market_data.edinet import EdinetProfitAndLoss
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class EdinetProfitAndLossRepository(BaseRepository[EdinetProfitAndLoss]):
    """Repository for `edinet_profit_and_loss`.

    Provides common queries and an UPSERT implementation targeting
    the unique pair `(sec_code, period_end_date)`.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository with an AsyncSession."""
        super().__init__(session, model=EdinetProfitAndLoss)

    async def find_latest_by_sec_code(self, sec_code: str) -> Optional[EdinetProfitAndLoss]:
        """Return the latest profit-and-loss record for a security code."""
        stmt = (
            select(self.model)
            .where(self.model.sec_code == sec_code)
            .order_by(self.model.period_end_date.desc(), self.model.submission_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_period(
        self, sec_code: str, period_end_date: date
    ) -> Optional[EdinetProfitAndLoss]:
        """Find a profit-and-loss record by security code and period end date."""
        result = await self.session.execute(
            select(self.model).where(
                self.model.sec_code == sec_code, self.model.period_end_date == period_end_date
            )
        )
        return result.scalar_one_or_none()

    async def find_by_doc_id(self, doc_id: str) -> List[EdinetProfitAndLoss]:
        """Return records matching the EDINET document id."""
        result = await self.session.execute(select(self.model).where(self.model.doc_id == doc_id))
        return list(result.scalars().all())

    async def upsert(self, data: dict) -> EdinetProfitAndLoss:
        """Insert or update a single record using SQLite ON CONFLICT UPSERT.

        Behavior:
        - Unique key: (`sec_code`, `period_end_date`)
        - When conflict occurs, update all columns except `id` and `created_at`.
        - Only overwrite when the incoming `submission_date` is newer or equal.
        """
        if not data:
            raise ValueError("data is required for upsert")

        table = self.model.__table__
        insert_stmt = insert(table).values(data)

        update_dict: dict[str, Any] = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name not in ("id", "created_at")
        }

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["sec_code", "period_end_date"],
            set_=update_dict,
            where=(insert_stmt.excluded.submission_date >= table.c.submission_date),
        )

        try:
            await self.session.execute(stmt)
            await self.session.flush()
            res = await self.find_by_period(data["sec_code"], data["period_end_date"])
            if res is None:
                raise RuntimeError("upsert succeeded but result not found")
            return res
        except SQLAlchemyError:
            logger.exception("upsert failed for edinet_profit_and_loss")
            raise

    async def get_latest_by_sec_codes(self, sec_codes: List[str]) -> List[EdinetProfitAndLoss]:
        """Get latest profit-and-loss records for multiple security codes."""
        if not sec_codes:
            return []

        stmt = (
            select(self.model)
            .where(self.model.sec_code.in_(sec_codes))
            .distinct(self.model.sec_code)
            .order_by(
                self.model.sec_code,
                self.model.period_end_date.desc(),
                self.model.submission_date.desc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_fiscal_year(
        self, sec_code: str, fiscal_year: int
    ) -> List[EdinetProfitAndLoss]:
        """Find profit-and-loss records for a given fiscal year and security code."""
        result = await self.session.execute(
            select(self.model)
            .where(self.model.sec_code == sec_code, self.model.fiscal_year == fiscal_year)
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def find_by_date_range(
        self, sec_code: str, start_date: date, end_date: date
    ) -> List[EdinetProfitAndLoss]:
        """Find profit-and-loss records within a date range for a security code."""
        result = await self.session.execute(
            select(self.model)
            .where(
                self.model.sec_code == sec_code,
                self.model.period_end_date >= start_date,
                self.model.period_end_date <= end_date,
            )
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def count_by_sec_code(self, sec_code: str) -> int:
        """Count profit-and-loss records for a given security code."""
        stmt = select(sql_count()).select_from(self.model).where(self.model.sec_code == sec_code)
        result = await self.session.execute(stmt)
        return result.scalar_one()


__all__ = ["EdinetProfitAndLossRepository"]
