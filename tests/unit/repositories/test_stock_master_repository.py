"""StockMasterRepository の単体テスト

テストは AAA パターン（Arrange / Act / Assert）で記述します。
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

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


@pytest.mark.asyncio
async def test_bulk_upsert_commits_on_success():
    # Arrange: モックセッションを用意
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()

    repo = StockMasterRepository(session=mock_session)

    records = [
        {
            "stock_code": "9999",
            "stock_name": "CommitTest",
            "market_category": "Prime",
        },
    ]

    # Act
    result = await repo.bulk_upsert(records)

    # Assert: commit が呼ばれていること
    assert result == 1
    mock_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_bulk_upsert_rolls_back_and_raises_on_sqlalchemy_error():
    # Arrange: モックセッションを用意して execute がエラーを投げる
    mock_session = AsyncMock()

    async def _raise(*args, **kwargs):
        raise SQLAlchemyError("boom")

    mock_session.execute = AsyncMock(side_effect=_raise)
    mock_session.flush = AsyncMock()
    mock_session.rollback = AsyncMock()

    repo = StockMasterRepository(session=mock_session)

    records = [
        {
            "stock_code": "0000",
            "stock_name": "ErrTest",
            "market_category": "Prime",
        },
    ]

    # Act / Assert: 例外が伝播し、rollback が呼ばれること
    with pytest.raises(SQLAlchemyError):
        await repo.bulk_upsert(records)

    mock_session.rollback.assert_awaited()
