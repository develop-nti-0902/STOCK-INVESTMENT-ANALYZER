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
        data: Dict[str, Any] = {}
        if processed is not None:
            data["processed_stocks"] = processed
        if total is not None:
            data["total_stocks"] = total
        if success is not None:
            data["successful_stocks"] = success
        if failed is not None:
            data["failed_stocks"] = failed

        if not data:
            return await self.repository.get(job_id)

        return await self.repository.update(record_id=job_id, data=data)

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

    async def __aenter__(self):
        self.job = await self.service.create_job(self.job_type, self.params)
        if self.job is None:
            raise RuntimeError("failed to create batch job")
        await self.service.start_job(self.job.id)

        class _Ctx:
            def __init__(self, parent: "BatchExecutionContext"):
                self._parent = parent

            async def update_progress(self, **kwargs):
                return await self._parent.service.update_progress(
                    self._parent.job.id, **kwargs
                )

            @property
            def job_id(self) -> int:
                return self._parent.job.id

        return _Ctx(self)

    async def __aexit__(self, exc_type, exc, tb):
        if self.job is None:
            return
        if exc:
            try:
                await self.service.fail_job(self.job.id, str(exc))
            except Exception:
                logger.exception("Failed to mark job failed: %s", self.job.id)
            return False

        try:
            # 完了時: 既存の集計値を取得して mark_completed を呼ぶ
            instance = await self.service.get_job_status(self.job.id)
            if instance is None:
                return
            success_count = int(getattr(instance, "successful_stocks", 0) or 0)
            failed_count = int(getattr(instance, "failed_stocks", 0) or 0)
            # If both zero, assume processed == success
            if success_count == 0 and failed_count == 0:
                processed = int(getattr(instance, "processed_stocks", 0) or 0)
                success_count = processed

            await self.service.complete_job(
                self.job.id,
                success_count=success_count,
                failed_count=failed_count,
            )
        except Exception:
            logger.exception("Failed to mark job completed: %s", self.job.id)


__all__ = ["BatchExecutionService", "BatchExecutionContext"]
