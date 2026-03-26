"""日経225日足データ Repository モジュール."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.nikkei225 import Nikkei2251d
from app.repositories.core.base import BaseRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei2251dRepository(BaseRepository[Nikkei2251d]):
    """日経225日足データ Repository.

    `timestamp` 単体をユニークキーとして UPSERT を行う。
    """

    def __init__(self, session: AsyncSession) -> None:
        """初期化."""
        super().__init__(session, model=Nikkei2251d)

    async def upsert_single(self, data: dict[str, Any]) -> dict[str, Any]:
        """単一レコード UPSERT — timestamp 単体で conflict 判定.

        Args:
            data: 挿入・更新するレコードデータ

        Returns:
            dict: rowcount と operation を含む結果情報
        """
        stmt = insert(Nikkei2251d).values(data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["timestamp"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "adj_close": stmt.excluded.adj_close,
                "volume": stmt.excluded.volume,
                "updated_at": text("CURRENT_TIMESTAMP"),
            },
        )
        result = cast(CursorResult, await self.session.execute(stmt))
        return {"rowcount": result.rowcount, "operation": "upsert"}

    async def upsert_bulk(self, records: list[dict[str, Any]]) -> int:
        """複数レコード UPSERT — バッチ分割で挿入.

        SQLite はバインドパラメータ上限があるため、バッチサイズを小さく分割する.

        Args:
            records: 挿入・更新するレコードデータのリスト

        Returns:
            int: 処理されたレコード数
        """
        if not records:
            return 0

        # SQLite のバインドパラメータ上限対策（1 バッチ500レコード）
        batch_size = 500
        total_rows = 0

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            stmt = insert(Nikkei2251d).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["timestamp"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "adj_close": stmt.excluded.adj_close,
                    "volume": stmt.excluded.volume,
                    "updated_at": text("CURRENT_TIMESTAMP"),
                },
            )
            result = cast(CursorResult, await self.session.execute(stmt))
            total_rows += result.rowcount

        await self.session.flush()
        return total_rows
