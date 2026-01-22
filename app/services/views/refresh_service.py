from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.exceptions.business import ServiceError
from app.services.batch.batch_execution_service import BatchExecutionService
from app.utils.database import get_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LatestStocksRefreshService:
    """`latest_stocks_1d` マテリアライズドビューのリフレッシュを管理するサービス。

    - `enqueue_refresh()` は `BatchExecutionService` を用いてジョブを登録し、実際にリフレッシュを実行する。
    - `run_refresh()` は実際にマテリアライズドビューをリフレッシュする実装を行う。

    Notes:
        - `REFRESH MATERIALIZED VIEW CONCURRENTLY` は非同期接続で実行します。
        - トランザクション外で実行する必要があるため、明示的にコミットを行います。
    """

    def __init__(
        self,
        batch_service: BatchExecutionService,
        engine: Optional[AsyncEngine] = None,
    ):
        self.batch_service = batch_service
        self._engine = engine

    async def enqueue_refresh(self) -> int:
        """BatchExecutionService にジョブを登録し、実際にリフレッシュを実行する。"""
        job = await self.batch_service.create_job("refresh_latest_stocks")
        if job is None:
            raise ServiceError(message="failed to create refresh job")

        job_id = int(getattr(job, "id"))

        try:
            # ジョブを開始状態にする
            await self.batch_service.start_job(job_id)

            # 実際にマテリアライズドビューをリフレッシュ
            await self.run_refresh()

            # ジョブを完了状態にする
            await self.batch_service.complete_job(
                job_id,
                success_count=0,
                failed_count=0,
            )
            logger.info(f"Refresh job {job_id} completed successfully")

        except Exception as e:
            # エラーが発生した場合はジョブを失敗状態にする
            await self.batch_service.fail_job(job_id, error_message=str(e))
            logger.error(f"Refresh job {job_id} failed: {e}")
            raise

        return job_id

    async def run_refresh(self) -> None:
        """実際にマテリアライズドビューをリフレッシュする。

        非同期エンジンを使用してマテリアライズドビューをリフレッシュします。
        REFRESH MATERIALIZED VIEW はトランザクション外で実行する必要があるため、
        autocommit モードで実行します。
        """

        engine = self._engine or get_engine()

        try:
            # autocommit モードで接続を取得してリフレッシュを実行
            async with engine.connect() as conn:
                # autocommit モードにするため execution_options を設定
                await conn.execute(
                    text(
                        "REFRESH MATERIALIZED VIEW CONCURRENTLY "
                        "latest_stocks_1d;"
                    )
                )
                # コミット（autocommitではないため明示的にコミット）
                await conn.commit()

            logger.info("Refreshed latest_stocks_1d successfully")
        except Exception as e:
            logger.exception("Refresh materialized view failed: %s", e)
            # Wrap low-level errors into ServiceError for callers
            raise ServiceError(
                message=f"failed to refresh latest_stocks_1d: {e}"
            )


__all__ = ["LatestStocksRefreshService"]
