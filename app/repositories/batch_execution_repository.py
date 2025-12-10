"""バッチ実行履歴用の Repository 実装モジュール。

このモジュールは `BatchExecution` モデルを扱うリポジトリを提供します。
テスト環境での AsyncMock 等に対応するため、BaseRepository の
ヘルパーを活用して awaitable な戻り値にも耐性を持たせています。
"""

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional, cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_execution import BatchExecution
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class BatchExecutionRepository(BaseRepository[BatchExecution]):
    """
    BatchExecution 専用の Repository

    提供する主要メソッド:
    - create_job
    - update_status
    - mark_completed
    - get_by_job_type
    - get_recent
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.model = BatchExecution

    async def create_job(self, job_type: str) -> BatchExecution:
        """新しいバッチ実行レコードを作成して返す"""
        # total_stocks は NULL 不可のため 0 で初期化する
        instance = self.model(
            batch_type=job_type,
            status="pending",
            total_stocks=0,
        )
        try:
            from app.utils.database import flush_commit_return

            maybe_res = cast(Any, self.session.add(instance))
            await self._maybe_await(maybe_res)
            return await flush_commit_return(self.session, instance)
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception("Failed to create batch job: %s", e)
            raise

    async def update_status(
        self, record_id: int, status: str
    ) -> Optional[BatchExecution]:
        """指定レコードのステータスを更新する"""
        instance = await self.get(record_id)
        if instance is None:
            return None
        instance.status = status
        from app.utils.database import flush_commit_return

        try:
            return await flush_commit_return(self.session, instance)
        except SQLAlchemyError as e:
            logger.exception("Failed to update status id=%s: %s", record_id, e)
            raise

    async def mark_completed(
        self,
        record_id: int,
        success_count: int,
        failed_count: int,
    ) -> Optional[BatchExecution]:
        """完了マークを付与して集計値と終了時刻を設定する"""
        instance = await self.get(record_id)
        if instance is None:
            return None

        instance.status = "completed"
        instance.successful_stocks = success_count
        instance.failed_stocks = failed_count
        instance.processed_stocks = success_count + failed_count
        instance.end_time = datetime.now(timezone.utc)

        from app.utils.database import flush_commit_return

        try:
            return await flush_commit_return(self.session, instance)
        except SQLAlchemyError as e:
            logger.exception(
                "Failed to mark completed id=%s: %s", record_id, e
            )
            raise

    async def get_by_job_type(self, job_type: str) -> List[BatchExecution]:
        """ジョブ種別で取得"""
        result = await self.session.execute(
            select(self.model).where(self.model.batch_type == job_type)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[BatchExecution]:
        """開始時間で降順に最近の実行履歴を取得"""
        result = await self.session.execute(
            select(self.model)
            .order_by(self.model.start_time.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


__all__ = ["BatchExecutionRepository"]
