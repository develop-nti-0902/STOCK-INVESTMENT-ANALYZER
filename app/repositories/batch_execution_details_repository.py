"""`BatchExecutionDetails` 用 Repository 実装.

提供メソッド:
 - init
 - inc
 - set_status
 - get_progress

トランザクション管理（commit/rollback）は上位層で行う想定です。
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_execution_details import BatchExecutionDetails
from app.repositories.core.base import BaseRepository
from app.utils.database import flush_return_with_log

logger = logging.getLogger(__name__)


class BatchExecutionDetailsRepository(BaseRepository[BatchExecutionDetails]):
    """`BatchExecutionDetails` 専用の Repository 実装."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `BatchExecutionDetails` モデルをセットします."""
        super().__init__(session, model=BatchExecutionDetails)

    async def init(
        self,
        batch_execution_id: int,
        interval: Optional[str] = None,
        total_stocks: int = 0,
        status: str = "pending",
    ) -> BatchExecutionDetails:
        """指定のバッチ・interval に対する集計レコードを初期化して返す."""
        instance = self.model(
            batch_execution_id=batch_execution_id,
            interval=interval,
            total_stocks=total_stocks,
            processed_stocks=0,
            successful_stocks=0,
            failed_stocks=0,
            status=status,
        )
        return await self._add_and_flush(instance)

    async def _find(self, batch_execution_id: int, interval: Optional[str]):
        result = await self.session.execute(
            select(self.model).where(
                self.model.batch_execution_id == batch_execution_id,
                self.model.interval == interval,
            )
        )
        return result.scalar_one_or_none()

    async def inc(
        self, batch_execution_id: int, interval: Optional[str], count: int = 1
    ) -> Optional[BatchExecutionDetails]:
        """処理済み件数をインクリメントする。該当レコードがなければ初期化してから更新する."""
        instance = await self._find(batch_execution_id, interval)
        if instance is None:
            instance = await self.init(batch_execution_id=batch_execution_id, interval=interval)

        # 安全に整数化して加算
        try:
            instance.processed_stocks = int(getattr(instance, "processed_stocks", 0)) + int(count)
        except Exception:
            instance.processed_stocks = (getattr(instance, "processed_stocks", 0) or 0) + count

        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush increment for batch=%s interval=%s",
            batch_execution_id,
            interval,
        )

    async def set_status(
        self, batch_execution_id: int, interval: Optional[str], status: str
    ) -> Optional[BatchExecutionDetails]:
        """指定レコードのステータスを更新する."""
        instance = await self._find(batch_execution_id, interval)
        if instance is None:
            return None
        instance.status = status
        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush set_status for batch=%s interval=%s",
            batch_execution_id,
            interval,
        )

    async def get_progress(self, batch_execution_id: int) -> List[BatchExecutionDetails]:
        """指定ジョブの interval ごとの進捗集計一覧を返す."""
        result = await self.session.execute(
            select(self.model).where(self.model.batch_execution_id == batch_execution_id)
        )
        return list(result.scalars().all())


__all__ = ["BatchExecutionDetailsRepository"]
