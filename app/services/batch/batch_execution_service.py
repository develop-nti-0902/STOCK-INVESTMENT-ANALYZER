from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.models.batch_execution import BatchExecution
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BatchExecutionService:
    """
    バッチ実行管理サービス

    リポジトリ層の `BatchExecutionRepository` を薄くラップして
    ビジネスロジック（状態遷移・コンテキスト管理）を提供します。
    """

    def __init__(self, repository: Any):
        self.repository = repository

    async def create_job(
        self, job_type: str, params: Optional[Dict] = None
    ) -> BatchExecution:
        if params is not None:
            logger.debug(
                "Creating batch job with type '%s' and params: %s",
                job_type,
                params,
            )

        return await self.repository.create_job(batch_type=job_type)

    async def start_job(self, job_id: int) -> Optional[BatchExecution]:
        return await self.repository.update_status(
            record_id=job_id, status="running"
        )

    async def update_progress(
        self,
        job_id: int,
        processed: Optional[int] = None,
        total: Optional[int] = None,
        success: Optional[int] = None,
        failed: Optional[int] = None,
    ) -> Optional[BatchExecution]:
        # 進捗値が指定されていない場合は、現在のジョブ状態を返す。
        if (
            processed is None
            and total is None
            and success is None
            and failed is None
        ):
            return await self.repository.get(job_id)

        # リポジトリ側の専用メソッド `update_progress` に処理を委譲する。
        # リポジトリ側では progress_data に次のキーを期待する:
        # 'processed', 'total', 'successful', 'failed'
        progress_data: Dict[str, Optional[int]] = {}
        if processed is not None:
            progress_data["processed"] = processed
        if total is not None:
            progress_data["total"] = total
        if success is not None:
            progress_data["successful"] = success
        if failed is not None:
            progress_data["failed"] = failed

        return await self.repository.update_progress(
            record_id=job_id, progress_data=progress_data
        )

    async def complete_job(
        self, job_id: int, success_count: int, failed_count: int
    ) -> Optional[BatchExecution]:
        return await self.repository.mark_completed(
            record_id=job_id,
            success_count=success_count,
            failed_count=failed_count,
        )

    async def fail_job(
        self, job_id: int, error_message: str
    ) -> Optional[BatchExecution]:
        data = {
            "status": "failed",
            "error_message": error_message,
            "end_time": datetime.now(timezone.utc),
        }
        return await self.repository.update(record_id=job_id, data=data)

    async def get_job_status(self, job_id: int) -> Optional[BatchExecution]:
        return await self.repository.get(job_id)

    async def get_recent_jobs(self, limit: int = 10):
        return await self.repository.get_recent(limit=limit)

    async def get_jobs_by_type(self, job_type: str):
        return await self.repository.get_by_job_type(batch_type=job_type)


class BatchExecutionContext:
    """async context manager for a batch job lifecycle

    使用例:
        async with BatchExecutionContext(service, job_type="jpx_all") as ctx:
            await do_work()
            await ctx.update_progress(processed=100, total=1000)
    """

    def __init__(
        self,
        service: BatchExecutionService,
        job_type: str,
        params: Optional[Dict] = None,
    ):
        self.service = service
        self.job_type = job_type
        self.params = params or {}
        self.job: Optional[BatchExecution] = None
        self.job_id: Optional[int] = None

    async def __aenter__(self):
        self.job = await self.service.create_job(self.job_type, self.params)
        if self.job is None:
            raise RuntimeError("failed to create batch job")

        # 安全に job_id を取り出して以降は int 型で扱う
        self.job_id = int(getattr(self.job, "id"))

        jid = self.job_id
        await self.service.start_job(jid)

        class _Ctx:
            def __init__(self, service: BatchExecutionService, job_id: int):
                self._service = service
                self._job_id = job_id

            async def update_progress(self, **kwargs):
                return await self._service.update_progress(
                    self._job_id, **kwargs
                )

            @property
            def job_id(self) -> int:
                return self._job_id

        return _Ctx(self.service, jid)

    async def __aexit__(self, exc_type, exc, tb):
        if self.job is None:
            return
        jid = self.job_id
        if jid is None:
            return
        if exc:
            try:
                await self.service.fail_job(jid, str(exc))
            except Exception:
                logger.exception("Failed to mark job failed: %s", jid)
            return False

        try:
            # 完了時: 既存の集計値を取得して mark_completed を呼ぶ
            instance = await self.service.get_job_status(jid)
            if instance is None:
                return
            success_count = int(getattr(instance, "successful_stocks", 0) or 0)
            failed_count = int(getattr(instance, "failed_stocks", 0) or 0)
            # If both zero, assume processed == success
            if success_count == 0 and failed_count == 0:
                processed = int(getattr(instance, "processed_stocks", 0) or 0)
                success_count = processed

            await self.service.complete_job(
                jid,
                success_count=success_count,
                failed_count=failed_count,
            )
        except Exception:
            logger.exception("Failed to mark job completed: %s", jid)


__all__ = ["BatchExecutionService", "BatchExecutionContext"]
