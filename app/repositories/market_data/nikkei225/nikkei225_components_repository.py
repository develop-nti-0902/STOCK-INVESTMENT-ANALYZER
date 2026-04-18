"""日経225構成銘柄リポジトリ."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.nikkei225 import Nikkei225Component
from app.repositories.core.base import BaseRepository


class Nikkei225ComponentRepository(BaseRepository[Nikkei225Component]):
    """日経225構成銘柄リポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        """リポジトリを初期化する."""
        super().__init__(session, model=Nikkei225Component)

    async def upsert_batch(self, data_list: list[dict]) -> list[Nikkei225Component]:
        """一括 upsert."""
        if not data_list:
            return []
        table = self.model.__table__
        insert_stmt = insert(table).values(data_list)
        update_dict = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name not in ("id", "created_at")
        }
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["stock_code", "effective_date"],
            set_=update_dict,
        ).returning(table)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return [self.model(**dict(row._mapping)) for row in result.fetchall()]

    async def find_by_code(self, stock_code: str) -> Nikkei225Component | None:
        """銘柄コードで最新レコードを取得."""
        stmt = (
            select(self.model)
            .where(self.model.stock_code == stock_code)
            .order_by(desc(self.model.effective_date))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
