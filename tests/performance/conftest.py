"""Performance test fixtures.

パフォーマンステスト用のfixture定義。実DB接続を使用します。
"""

# flake8: noqa

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.main import app as fastapi_app
from app.repositories.market_data.stock_master import (
    StockCodeMappingRepository,
    StockMasterRepository,
    StockMasterUpdatesRepository,
)
from app.utils.database import get_database_url


def _run_async(coro):
    """非同期関数を同期コンテキストで実行するヘルパー."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


@pytest.fixture(scope="function")
def perf_client():
    """パフォーマンステスト用の実DB接続を備えたTestClient.

    E2Eテストと同様に、実DBに接続します（モック不使用）。
    """
    try:
        with TestClient(fastapi_app) as tc:
            yield tc
    finally:
        pass


@pytest.fixture(scope="function")
def setup_perf_test_db():
    """パフォーマンステスト実行前のDB準備とクリーンアップ.

    テスト対象テーブルを削除し、クリーンな状態にします：
    - stock_masters
    - stock_code_mappings
    - stock_master_updates

    Yields:
        None（クリーンアップ完了後）
    """

    async def _cleanup():
        """非同期クリーンアップ処理."""
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                # 各リポジトリの delete メソッドでクリーンアップ
                repo = StockMasterRepository(session=session)
                await repo.delete_all()

                code_mapping_repo = StockCodeMappingRepository(session=session)
                await code_mapping_repo.delete_all()

                updates_repo = StockMasterUpdatesRepository(session=session)
                await updates_repo.delete_by_reset()

                await session.commit()
        finally:
            await engine.dispose()

    # テスト前: DB クリーンアップ
    _run_async(_cleanup())

    yield

    # テスト後: DB クリーンアップ（残存データ削除）
    _run_async(_cleanup())
