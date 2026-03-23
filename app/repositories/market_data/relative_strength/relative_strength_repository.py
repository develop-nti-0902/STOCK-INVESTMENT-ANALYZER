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

_UPSERT_CHUNK_SIZE = 2500


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
        total_rowcount = 0

        for i in range(0, len(records), _UPSERT_CHUNK_SIZE):
            chunk = records[i : i + _UPSERT_CHUNK_SIZE]
            stmt = insert(table).values(chunk)

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
                total_rowcount += rowcount or len(chunk)
            except Exception:
                logger.exception("Failed to upsert relative strength records")
                raise

        return total_rowcount

    async def delete_all(self) -> int:
        """全件削除."""
        result = cast(CursorResult, await self.session.execute(delete(self.model)))
        return result.rowcount or 0
