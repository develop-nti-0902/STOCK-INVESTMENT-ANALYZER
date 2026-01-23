from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.exceptions.business import ServiceError
from app.services.batch.batch_execution_service import BatchExecutionService
from app.services.views.base import BaseViewService
from app.utils.database import get_engine


class LatestStocksRefreshService(BaseViewService):
    """`latest_stocks_1d` マテリアライズドビューのリフレッシュを管理するサービス。"""

    def __init__(
        self,
        batch_service: BatchExecutionService,
        engine: Optional[AsyncEngine] = None,
    ):
        super().__init__()
        self.batch_service = batch_service
        self._engine = engine

    async def enqueue_refresh(self) -> int:
        job = await self.batch_service.create_job("refresh_latest_stocks")
        if job is None:
            raise ServiceError(message="failed to create refresh job")

        job_id = int(getattr(job, "id"))

        try:
            await self.batch_service.start_job(job_id)
            await self.run_refresh()
            await self.batch_service.complete_job(
                job_id, success_count=0, failed_count=0
            )
            self.logger.info(f"Refresh job {job_id} completed successfully")

        except Exception as e:
            await self.batch_service.fail_job(job_id, error_message=str(e))
            self.logger.error(f"Refresh job {job_id} failed: {e}")
            raise

        return job_id

    async def run_refresh(self) -> None:
        engine = self._engine or get_engine()

        try:
            async with engine.connect() as conn:
                await conn.execute(
                    text(
                        "REFRESH MATERIALIZED VIEW CONCURRENTLY "
                        "latest_stocks_1d;"
                    )
                )
                await conn.commit()

            self.logger.info("Refreshed latest_stocks_1d successfully")
        except Exception as e:
            self.logger.exception("Refresh materialized view failed: %s", e)
            raise ServiceError(
                message=f"failed to refresh latest_stocks_1d: {e}"
            )


__all__ = ["LatestStocksRefreshService"]
