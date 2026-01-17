"""`stock_master_updates` テーブル向けの Repository 実装.

基本的な create/update/delete/get 操作を提供します。
"""

import logging
from typing import Dict, Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.database import MasterDataError
from app.models.stock_master_updates import StockMasterUpdates
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class StockMasterUpdatesRepository(BaseRepository[StockMasterUpdates]):
    """`stock_master_updates` 向け Repository.

    サービス層から呼び出される最小の CRUD を提供します。
    トランザクション制御（コミット/ロールバック）は上位のサービス層が行います。
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, StockMasterUpdates)

    async def create_summary(self, data: Dict) -> StockMasterUpdates:
        """リフレッシュ開始時のサマリレコードを作成して返す。"""
        try:
            return await self.create(data)
        except Exception as e:
            logger.exception(
                "Failed to create stock_master_update summary: %s", e
            )
            raise MasterDataError(
                message=f"Failed to create summary: {e}"
            ) from e

    async def update_status(
        self, record_id: int, status: str, extra: Optional[Dict] = None
    ) -> Optional[StockMasterUpdates]:
        """レコードの `status` と追加フィールドを更新して更新後インスタンスを返す。

        Args:
            record_id: 対象レコードの ID
            status: 更新後のステータス文字列（例: 'running','success','failed'）
            extra: `completed_at` や統計値などの追加フィールドを含む辞書
        """
        if extra is None:
            extra = {}

        payload = {"status": status, **extra}
        try:
            return await self.update(record_id, payload)
        except Exception as e:
            logger.exception(
                "Failed to update status for stock_master_update id=%s: %s",
                record_id,
                e,
            )
            raise MasterDataError(
                message=f"Failed to update status: {e}"
            ) from e

    async def delete_by_reset(self) -> int:
        """リセット実行時に `stock_master_updates` の全レコードを削除する。

        Returns:
            int: 削除された件数
        """
        try:
            stmt = sql_delete(self.model)
            result = await self.session.execute(stmt)

            # mypy 対応:
            # Result が静的に 'rowcount' を持たない可能性があるため getattr を使用
            deleted_count = int(getattr(result, "rowcount", 0) or 0)
            logger.info(
                "Deleted %d stock_master_updates records", deleted_count
            )
            return deleted_count
        except Exception as e:
            logger.exception(
                "Failed to delete stock_master_updates records: %s", e
            )
            raise MasterDataError(
                message=f"Failed to delete records: {e}"
            ) from e

    async def get_by_id(self, record_id: int) -> Optional[StockMasterUpdates]:
        """ID による単一レコード取得。"""
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == record_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.exception(
                "Failed to get stock_master_update id=%s: %s", record_id, e
            )
            raise MasterDataError(message=f"Failed to get record: {e}") from e


__all__ = ["StockMasterUpdatesRepository"]
