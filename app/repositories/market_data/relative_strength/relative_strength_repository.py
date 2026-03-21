"""レラティブストレングスリポジトリ実装."""

from __future__ import annotations

import logging
from typing import Any, List, cast

from sqlalchemy import delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.relative_strength import RelativeStrength
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)


class RelativeStrengthRepository(BaseRepository[RelativeStrength]):
    """レラティブストレングスリポジトリ."""

    def __init__(self, session: AsyncSession) -> None:
        """AsyncSession を受け取り、RelativeStrength モデルで初期化します."""
        super().__init__(session, model=RelativeStrength)

    async def bulk_upsert(self, records: List[dict[str, Any]]) -> int:
        """(symbol, calculation_date) をキーとしたバッチUPSERT."""
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
            index_elements=["symbol", "calculation_date"],
            set_=update_dict,
        )

        try:
            result = await self.session.execute(stmt)
            rowcount = getattr(result, "rowcount", None)
            return rowcount or len(records)
        except Exception:
            logger.exception("Failed to upsert relative strength records")
            raise

    async def delete_all(self) -> int:
        """全件削除."""
        result = cast(CursorResult, await self.session.execute(delete(self.model)))
        return result.rowcount or 0
