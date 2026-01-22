from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import text

from app.exceptions.business import ServiceError
from app.utils.database import get_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LatestStocksRefreshService:
    """`latest_stocks_1d` マテリアライズドビューのリフレッシュを管理するサービス。

    - `enqueue_refresh()` は `BatchExecutionService` を用いてジョブを登録し、ジョブIDを返す。
    - `run_refresh()` は実際にマテリアライズドビューをリフレッシュする実装を行う。

    Notes:
        - `REFRESH MATERIALIZED VIEW CONCURRENTLY` はトランザクション外で実行する必要があるため
          sync エンジンで実行する実装になっています。
    """

    def __init__(self, batch_service: object, engine: Optional[object] = None):
        self.batch_service = batch_service
        self._engine = engine

    async def enqueue_refresh(self) -> int:
        """BatchExecutionService にジョブを登録してジョブIDを返す。"""
        job = await self.batch_service.create_job("refresh_latest_stocks")
        if job is None:
            raise ServiceError(message="failed to create refresh job")
        return int(getattr(job, "id"))

    async def run_refresh(self) -> None:
        """実際にマテリアライズドビューをリフレッシュする。

        同期実行が必要なため、内部で同期的に接続を取得して実行し、
        非同期のコンテキストからはスレッドで実行します。
        """

        engine = self._engine or get_engine()

        def _do_refresh() -> None:
            try:
                sync_engine = engine.sync_engine
                with sync_engine.connect() as conn:
                    sql = (
                        "REFRESH MATERIALIZED VIEW CONCURRENTLY "
                        "latest_stocks_1d;"
                    )
                    conn.execute(text(sql))
            except Exception as e:  # pragma: no cover - logging path
                logger.exception("Refresh materialized view failed: %s", e)
                raise

        try:
            await asyncio.get_running_loop().run_in_executor(None, _do_refresh)
            logger.info("Refreshed latest_stocks_1d successfully")
        except Exception as e:
            # Wrap low-level errors into ServiceError for callers
            raise ServiceError(
                message=f"failed to refresh latest_stocks_1d: {e}"
            )


__all__ = ["LatestStocksRefreshService"]
