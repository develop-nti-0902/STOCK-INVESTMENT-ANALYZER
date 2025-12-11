"""バッチ実行履歴用の Repository 実装モジュール。

このモジュールは `BatchExecution` モデルを扱うリポジトリを提供します。
テスト環境での AsyncMock 等に対応するため、BaseRepository の
ヘルパーを活用して awaitable な戻り値にも耐性を持たせています。
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_execution import BatchExecution
from app.repositories.base import BaseRepository
from app.utils.config import get_settings
from app.utils.database import flush_commit_return_with_log

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
        super().__init__(session, model=BatchExecution)

    async def create_job(self, batch_type: str) -> BatchExecution:
        """新しいバッチ実行レコードを作成して返す"""
        # total_stocks は NULL 不可のため 0 で初期化する
        instance = self.model(
            batch_type=batch_type,
            status="pending",
            total_stocks=0,
        )
        return await self._add_and_commit(instance)

    async def update_status(
        self, record_id: int, status: str
    ) -> Optional[BatchExecution]:
        """指定レコードのステータスを更新する"""
        instance = await self.get(record_id)
        if instance is None:
            return None
        instance.status = status

        return await flush_commit_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to update status id=%s",
            record_id,
        )

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

        return await flush_commit_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to mark completed id=%s",
            record_id,
        )

    async def get_by_job_type(self, batch_type: str) -> List[BatchExecution]:
        """ジョブ種別（batch_type）で取得"""
        result = await self.session.execute(
            select(self.model).where(self.model.batch_type == batch_type)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[BatchExecution]:
        """開始時間で降順に最近の実行履歴を取得"""
        # パラメータ検証: 負の値や過剰な値を許容しない
        if limit <= 0:
            raise ValueError("limit must be positive")
        # 設定から上限を取得（環境や運用で調整可能）
        settings = get_settings()
        max_limit = settings.MAX_RECENT_LIMIT
        if limit > max_limit:
            raise ValueError(f"limit too large; max={max_limit}")
        result = await self.session.execute(
            select(self.model)
            .order_by(self.model.start_time.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


__all__ = ["BatchExecutionRepository"]
