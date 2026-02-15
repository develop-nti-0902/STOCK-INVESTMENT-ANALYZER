"""バッチ実行履歴用の Repository 実装モジュール.

`BatchExecution` モデル用のデータアクセスを提供します。テスト環境の
awaitable な戻り値にも対応するため BaseRepository のヘルパーを利用しています。
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch_execution import BatchExecution
from app.models.enums import BatchExecutionStatus
from app.repositories.core.base import BaseRepository
from app.utils.database import flush_return_with_log
from app.utils.validation import validate_pagination

logger = logging.getLogger(__name__)


class BatchExecutionRepository(BaseRepository[BatchExecution]):
    """`BatchExecution` 専用の Repository.

    主な提供メソッド:
        - create_job
        - update_status
        - mark_completed
        - get_by_job_type
        - get_recent
    """

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `BatchExecution` モデルをセットします."""
        super().__init__(session, model=BatchExecution)

    async def create_job(self, batch_type: str) -> BatchExecution:
        """新しいバッチ実行レコードを作成して返す.

        Args:
            batch_type (str): バッチ種別識別子

        Returns:
            BatchExecution: 作成されたジョブレコード

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        # total_stocks は NULL 不可のため 0 で初期化する
        instance = self.model(
            batch_type=batch_type,
            status=BatchExecutionStatus.PENDING,
            total_stocks=0,
        )
        return await self._add_and_flush(instance)

    async def update_status(
        self, record_id: int, status: Union[BatchExecutionStatus, str]
    ) -> Optional[BatchExecution]:
        """指定レコードのステータスを更新する.

        Args:
            record_id (int): 更新対象のレコード ID
            status (str): 新しいステータス文字列

        Returns:
            Optional[BatchExecution]: 更新後のインスタンス、存在しなければ None

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        instance = await self.get(record_id)
        if instance is None:
            return None
        # Accept either BatchExecutionStatus or its string value
        if isinstance(status, str):
            status = BatchExecutionStatus(status)
        instance.status = status

        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush status update id=%s",
            record_id,
        )

    async def mark_completed(
        self,
        record_id: int,
        success_count: int,
        failed_count: int,
    ) -> Optional[BatchExecution]:
        """完了マークを付与し集計値と終了時刻を設定する.

        Args:
            record_id (int): ジョブ ID
            success_count (int): 成功件数
            failed_count (int): 失敗件数

        Returns:
            Optional[BatchExecution]: 更新後のインスタンス、存在しなければ None

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        instance = await self.get(record_id)
        if instance is None:
            return None

        instance.status = BatchExecutionStatus.COMPLETED
        instance.successful_stocks = success_count
        instance.failed_stocks = failed_count
        instance.processed_stocks = success_count + failed_count
        instance.end_time = datetime.now(timezone.utc)

        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush mark completed id=%s",
            record_id,
        )

    async def get_by_job_type(self, batch_type: str) -> List[BatchExecution]:
        """ジョブ種別（batch_type）でレコード一覧を取得する.

        Args:
            batch_type (str): 対象のバッチ種別

        Returns:
            List[BatchExecution]: 該当レコードのリスト
        """
        result = await self.session.execute(
            select(self.model).where(self.model.batch_type == batch_type)
        )
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 10) -> List[BatchExecution]:
        """開始時間で降順に最近の実行履歴を取得する.

        Args:
            limit (int): 取得上限件数（デフォルト: 10）

        Returns:
            List[BatchExecution]: 最近実行されたジョブ一覧
        """
        # パラメータ検証: 共通ユーティリティへ移譲
        validate_pagination(0, limit)
        result = await self.session.execute(
            select(self.model).order_by(self.model.start_time.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def update_progress(
        self,
        record_id: int,
        progress_data: dict,
    ) -> Optional[BatchExecution]:
        """進捗情報を更新する.

        Args:
            record_id (int): ジョブ ID
            progress_data (dict): 進捗情報を表す辞書。受け付けるキー:
                - processed: 処理済数
                - successful: 成功数
                - failed: 失敗数
                - total: 総対象数

        Returns:
            Optional[BatchExecution]: 更新後のインスタンス、存在しなければ None
        """
        instance = await self.get(record_id)
        if instance is None:
            return None

        if "processed" in progress_data:
            instance.processed_stocks = int(progress_data["processed"])
        if "successful" in progress_data:
            instance.successful_stocks = int(progress_data["successful"])
        if "failed" in progress_data:
            instance.failed_stocks = int(progress_data["failed"])
        if "total" in progress_data:
            instance.total_stocks = int(progress_data["total"])

        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush progress update id=%s",
            record_id,
        )

    async def get_running_jobs(self) -> List[BatchExecution]:
        """実行中のジョブ（status == 'running'）を取得する.

        Returns:
            List[BatchExecution]: 実行中ジョブのリスト
        """
        result = await self.session.execute(
            select(self.model).where(self.model.status == BatchExecutionStatus.RUNNING)
        )
        return list(result.scalars().all())

    async def cancel_job(
        self,
        record_id: int,
    ) -> Optional[BatchExecution]:
        """ジョブをキャンセルして終了時刻を記録する.

        Args:
            record_id (int): キャンセル対象のジョブ ID

        Returns:
            Optional[BatchExecution]: 更新後のインスタンス、存在しなければ None

        Notes:
            ステータスは 'cancelled' に設定します。
        """
        instance = await self.get(record_id)
        if instance is None:
            return None

        instance.status = BatchExecutionStatus.CANCELLED
        instance.end_time = datetime.now(timezone.utc)

        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush cancel job id=%s",
            record_id,
        )


__all__ = ["BatchExecutionRepository"]
