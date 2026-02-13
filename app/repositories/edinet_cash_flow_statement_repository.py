"""EDINET キャッシュフロー用 Repository 実装.

`edinet_profit_and_loss_repository.py` を参考に UPSERT 等のコア操作を実装します.
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

from app.models.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class EdinetCashFlowStatementRepository(BaseRepository[EdinetCashFlowStatement]):
    """`edinet_cash_flow_statement` テーブル向けの Repository 実装.

    UPSERT を用いた登録/更新を提供します。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=EdinetCashFlowStatement)

    async def find_latest_by_sec_code(self, sec_code: str) -> Optional[EdinetCashFlowStatement]:
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
    ) -> Optional[EdinetCashFlowStatement]:
        result = await self.session.execute(
            select(self.model).where(
                self.model.sec_code == sec_code,
                self.model.period_end_date == period_end_date,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_doc_id(self, doc_id: str) -> List[EdinetCashFlowStatement]:
        result = await self.session.execute(select(self.model).where(self.model.doc_id == doc_id))
        return list(result.scalars().all())

    async def upsert(self, data: dict) -> EdinetCashFlowStatement:
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
        except SQLAlchemyError as e:
            logger.exception("edinet cash flow upsert failed: %s", e)
            raise

    async def get_latest_by_sec_codes(self, sec_codes: List[str]) -> List[EdinetCashFlowStatement]:
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
    ) -> List[EdinetCashFlowStatement]:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.sec_code == sec_code, self.model.fiscal_year == fiscal_year)
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def find_by_date_range(
        self, sec_code: str, start_date: date, end_date: date
    ) -> List[EdinetCashFlowStatement]:
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
        stmt = select(sql_count()).select_from(self.model).where(self.model.sec_code == sec_code)
        result = await self.session.execute(stmt)
        return result.scalar_one()


__all__ = ["EdinetCashFlowStatementRepository"]
