"""配当利回り履歴リポジトリ実装。"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, List

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.dividend_yield_history import DividendYieldHistory
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)


class DividendYieldHistoryRepository(BaseRepository[DividendYieldHistory]):
    """配当利回り履歴リポジトリ。

    DIVIDEND_YIELD_HISTORY テーブルへのデータアクセスを提供。
    UPSERT、削除、範囲検索をサポート。
    """

    def __init__(self, session: AsyncSession) -> None:
        """初期化。

        Args:
            session: 非同期DB セッション
        """
        super().__init__(session, model=DividendYieldHistory)

    async def bulk_upsert(self, records: List[dict[str, Any]]) -> int:
        """バッチ UPSERT を実行。

        `(symbol, date)` をキーとした UPSERT。
        既存レコードがある場合は更新、ない場合は新規挿入。
        `created_at` は保護（更新対象外）して初回の作成時刻を保持。

        Args:
            records: 挿入/更新するレコード辞書のリスト

        Returns:
            処理されたレコード数

        Raises:
            例外は log.exception でログして raise
        """
        if not records:
            return 0

        table = self.model.__table__
        stmt = insert(table).values(records)

        # UPDATEするカラムを、id と created_at を除いてすべて対象
        update_dict = {
            column.name: getattr(stmt.excluded, column.name)
            for column in table.c
            if column.name not in ("id", "created_at")
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_=update_dict,
        )

        try:
            result = await self.session.execute(stmt)
            rowcount = getattr(result, "rowcount", None)
            return rowcount or len(records)
        except Exception:
            logger.exception("Failed to upsert dividend yield history records")
            raise

    async def get_by_symbol_date_range(
        self, symbol: str, start_date: date, end_date: date
    ) -> List[DividendYieldHistory]:
        """指定銘柄の期間別レコードを取得。

        Args:
            symbol: 銘柄コード
            start_date: 開始日付（含む）
            end_date: 終了日付（含む）

        Returns:
            レコードのリスト（日付昇順）
        """
        stmt = (
            select(self.model)
            .where(
                (self.model.symbol == symbol)
                & (self.model.date >= start_date)
                & (self.model.date <= end_date)
            )
            .order_by(self.model.date)
        )

        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception:
            logger.exception(
                "Failed to fetch dividend yield history for %s [%s - %s]",
                symbol,
                start_date,
                end_date,
            )
            raise

    async def delete_by_date_range(self, start_date: date, end_date: date) -> int:
        """指定期間のレコードをすべて削除。

        Args:
            start_date: 開始日付（含む）
            end_date: 終了日付（含む）

        Returns:
            削除したレコード数
        """
        stmt = delete(self.model).where(
            (self.model.date >= start_date) & (self.model.date <= end_date)
        )

        try:
            result = await self.session.execute(stmt)
            rowcount = getattr(result, "rowcount", None)
            return rowcount or 0
        except Exception:
            logger.exception(
                "Failed to delete dividend yield history records [%s - %s]",
                start_date,
                end_date,
            )
            raise


__all__ = ["DividendYieldHistoryRepository"]
