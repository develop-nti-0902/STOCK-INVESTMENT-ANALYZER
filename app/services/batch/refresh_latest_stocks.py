from __future__ import annotations

import asyncio
from typing import Optional

from sqlalchemy import text

from app.services.batch.batch_execution_service import BatchExecutionContext
from app.services.views.refresh_service import LatestStocksRefreshService
from app.utils.database import get_engine
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def refresh_latest_stocks_job(
    batch_service: object, engine: Optional[object] = None, lock_key: int = 1
) -> None:
    """バッチジョブ: `REFRESH MATERIALIZED VIEW CONCURRENTLY latest_stocks_1d` を実行する。

    - `BatchExecutionContext` を使ってジョブライフサイクルを管理する。
    - PostgreSQL の advisory lock を取得して同時実行を防止する。
    """

    engine = engine or get_engine()

    def _try_acquire() -> bool:
        try:
            sync_engine = engine.sync_engine
            with sync_engine.connect() as conn:
                res = conn.execute(
                    text("SELECT pg_try_advisory_lock(:k)"), {"k": lock_key}
                )
                row = res.fetchone()
                return bool(row[0]) if row is not None else False
        except Exception as e:  # pragma: no cover - DB error path
            logger.exception("Failed to acquire advisory lock: %s", e)
            return False

    def _release() -> bool:
        try:
            sync_engine = engine.sync_engine
            with sync_engine.connect() as conn:
                res = conn.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": lock_key}
                )
                row = res.fetchone()
                return bool(row[0]) if row is not None else False
        except Exception as e:  # pragma: no cover - DB error path
            logger.exception("Failed to release advisory lock: %s", e)
            return False

    refresh_service = LatestStocksRefreshService(
        batch_service=batch_service, engine=engine
    )

    loop = asyncio.get_running_loop()

    async with BatchExecutionContext(
        batch_service, job_type="refresh_latest_stocks"
    ):
        acquired = await loop.run_in_executor(None, _try_acquire)
        if not acquired:
            logger.warning(
                "Could not acquire advisory lock for refresh job: %s", lock_key
            )
            return

        try:
            await refresh_service.run_refresh()
        except Exception as e:
            logger.exception(
                "Exception during refresh_latest_stocks_job: %s", e
            )
            raise
        finally:
            released = await loop.run_in_executor(None, _release)
            if not released:
                logger.error(
                    "Failed to release advisory lock for job: %s", lock_key
                )


__all__ = ["refresh_latest_stocks_job"]
