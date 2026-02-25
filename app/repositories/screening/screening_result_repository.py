"""screening_results テーブルへのアクセスを提供するリポジトリ."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.screening import ScreeningResult
from app.repositories.core.base import BaseRepository
from app.utils.validation import validate_pagination

logger = logging.getLogger(__name__)


class ScreeningResultRepository(BaseRepository[ScreeningResult]):
    """ScreeningResult モデル用のデータアクセスを提供します."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=ScreeningResult)

    async def upsert(self, data: Dict[str, Any]) -> ScreeningResult:
        """複数カラムで一意に upsert を行い、保存済レコードを返します."""
        if not data:
            raise ValueError("data is required for upsert")

        table = self.model.__table__
        insert_stmt = insert(table).values(data)
        update_dict = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name not in ("id", "created_at")
        }
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["symbol", "evaluation_date"],
            set_=update_dict,
            where=(insert_stmt.excluded.evaluation_date >= table.c.evaluation_date),
        )

        try:
            await self.session.execute(stmt)
            await self.session.flush()
            result = await self.find_latest_by_symbol(data["symbol"])
            if result is None:
                raise RuntimeError("upsert succeeded but result not found")
            return result
        except SQLAlchemyError:
            logger.exception("upsert failed for screening_results")
            raise

    async def find_latest_by_symbol(self, symbol: str) -> Optional[ScreeningResult]:
        """指定銘柄の最新スクリーニング結果を返します."""
        stmt = (
            select(self.model)
            .where(self.model.symbol == symbol)
            .order_by(self.model.evaluation_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_symbol(self, symbol: str) -> List[ScreeningResult]:
        """指定銘柄に対して過去スクリーニング結果を全件取得します."""
        stmt = (
            select(self.model)
            .where(self.model.symbol == symbol)
            .order_by(self.model.evaluation_date.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        min_score: Optional[int] = None,
        status: Optional[str] = None,
        symbols: Optional[List[str]] = None,
    ) -> List[ScreeningResult]:
        """条件を指定してスクリーニング結果をページング取得します."""
        validate_pagination(skip, limit)

        stmt = select(self.model)
        if status:
            stmt = stmt.where(self.model.status == status)
        if min_score is not None:
            stmt = stmt.where(self.model.total_score >= min_score)
        if symbols:
            stmt = stmt.where(self.model.symbol.in_(symbols))

        stmt = (
            stmt.order_by(
                self.model.total_score.desc(),
                self.model.evaluation_date.desc(),
            )
            .limit(limit)
            .offset(skip)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


__all__ = ["ScreeningResultRepository"]
