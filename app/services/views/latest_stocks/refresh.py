"""最新株価ビューのリフレッシュを扱うサービスモジュール.

`latest_stocks_1d` マテリアライズドビューの更新ジョブ作成と実行を提供します.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.exceptions.business import ServiceError
from app.services.batch.batch_execution_service import BatchExecutionService
from app.services.views.base import BaseViewService
from app.utils.database import get_engine


class LatestStocksRefreshService(BaseViewService):
    """`latest_stocks_1d` マテリアライズドビューのリフレッシュを管理するサービス.

    Attributes:
        batch_service: バッチ管理サービス
        _engine: DB 接続エンジン（テスト用に注入可能）
    """

    def __init__(
        self,
        batch_service: BatchExecutionService,
        engine: Optional[AsyncEngine] = None,
    ):
        """インスタンスを初期化する.

        Args:
            batch_service: バッチ管理サービス
            engine: オプションの AsyncEngine（未指定時は `get_engine()` を使用）
        """
        super().__init__()
        self.batch_service = batch_service
        self._engine = engine

    async def enqueue_refresh(self, lock_key: int = 1) -> int:
        """リフレッシュジョブを作成して即時実行する.

        PostgreSQL のトランザクションレベル advisory lock を使用して同時実行を防止します。

        Args:
            lock_key: PostgreSQL advisory lock のキー（デフォルト: 1）

        Returns:
            作成されたジョブの ID

        Raises:
            ServiceError: ロックが取得できない場合、またはリフレッシュに失敗した場合
        """
        engine = self._engine or get_engine()

        # トランザクションレベル advisory lock を使用
        # (トランザクション終了時に自動解放される)
        try:
            async with engine.connect() as conn:
                async with conn.begin():
                    # トランザクションレベルのロックを取得
                    result = await conn.execute(
                        text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": lock_key}
                    )
                    row = result.fetchone()
                    acquired = bool(row[0]) if row is not None else False

                    if not acquired:
                        self.logger.warning(
                            "Could not acquire advisory lock for refresh job: %s", lock_key
                        )
                        raise ServiceError(
                            message=f"Refresh job is already running (lock_key={lock_key})"
                        )

                    # ロック取得成功、ジョブ作成へ
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
                    # トランザクション終了時にロックは自動解放される

        except ServiceError:
            # すでに適切な ServiceError としてラップされている
            raise
        except Exception as e:
            self.logger.exception("Unexpected error in enqueue_refresh: %s", e)
            raise ServiceError(message=f"Failed to enqueue refresh job: {e}")

    async def run_refresh(self) -> None:
        """`latest_stocks_1d` マテリアライズドビューをデータベース上で更新する.

        Raises:
            ServiceError: リフレッシュ処理が失敗した場合
        """
        engine = self._engine or get_engine()

        try:
            async with engine.connect() as conn:
                await conn.execute(
                    text("REFRESH MATERIALIZED VIEW CONCURRENTLY " "latest_stocks_1d;")
                )
                await conn.commit()

            self.logger.info("Refreshed latest_stocks_1d successfully")
        except Exception as e:
            self.logger.exception("Refresh materialized view failed: %s", e)
            raise ServiceError(message=f"failed to refresh latest_stocks_1d: {e}")


__all__ = ["LatestStocksRefreshService"]
