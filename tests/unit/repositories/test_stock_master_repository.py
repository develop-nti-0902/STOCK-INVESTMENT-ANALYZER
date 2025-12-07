"""StockMasterRepository の単体テスト

テストは AAA パターン（Arrange / Act / Assert）で記述します。
"""

from unittest.mock import AsyncMock

import pytest

from app.repositories.stock_master_repository import StockMasterRepository


@pytest.mark.asyncio
async def test_bulk_upsert_returns_zero_for_empty_records():
    # Arrange: モックセッションを用意
    mock_session = AsyncMock()
    repo = StockMasterRepository(session=mock_session)

    # Act: 空リストを渡す
    result = await repo.bulk_upsert([])

    # Assert: 0 を返し、DB操作は呼ばれない
    assert result == 0
    mock_session.execute.assert_not_awaited()
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_upsert_executes_insert_and_flush():
    # Arrange: モックセッションを用意
    mock_session = AsyncMock()
    # execute/flush は非同期で呼ばれる想定
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()

    repo = StockMasterRepository(session=mock_session)

    records = [
        {
            "stock_code": "1301",
            "stock_name": "Test Co",
            "market_category": "Prime",
        },
        {
            "stock_code": "1332",
            "stock_name": "Test2 Co",
            "market_category": "Prime",
        },
    ]

    # Act: bulk_upsert を実行
    result = await repo.bulk_upsert(records)

    # Assert: 入力件数を返すこと、execute と flush が呼ばれること
    assert result == len(records)
    mock_session.execute.assert_awaited()
    mock_session.flush.assert_awaited()
