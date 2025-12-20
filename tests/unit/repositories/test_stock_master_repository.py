"""StockMasterRepository の単体テスト

テストは AAA パターン（Arrange / Act / Assert）で記述します。
"""

from unittest.mock import AsyncMock, Mock

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


@pytest.mark.asyncio
async def test_get_by_symbol_calls_execute_and_returns_instance():
    mock_session = AsyncMock()
    repo = StockMasterRepository(session=mock_session)

    # Arrange: 期待インスタンスを用意
    expected = object()
    fake_result = Mock()
    # scalar_one_or_none は同期的に呼ばれるため属性で用意
    fake_result.scalar_one_or_none = lambda: expected
    mock_session.execute.return_value = fake_result

    # Act
    res = await repo.get_by_symbol("AAA")

    # Assert
    mock_session.execute.assert_awaited()
    assert res is expected


@pytest.mark.asyncio
async def test_get_by_market_and_search_return_list():
    mock_session = AsyncMock()
    repo = StockMasterRepository(session=mock_session)

    expected1 = object()
    expected2 = object()

    fake_result = Mock()
    fake_result.scalars.return_value.all.return_value = [expected1, expected2]
    mock_session.execute.return_value = fake_result

    res_market = await repo.get_by_market("Prime")
    res_search = await repo.search("Test")

    assert res_market == [expected1, expected2]
    assert res_search == [expected1, expected2]


@pytest.mark.asyncio
async def test_upsert_is_not_supported():
    mock_session = AsyncMock()
    repo = StockMasterRepository(session=mock_session)

    data = {"stock_code": "ZZZ", "stock_name": "Z"}

    with pytest.raises(NotImplementedError):
        await repo.upsert(data)


@pytest.mark.asyncio
async def test_get_all_active_symbols_success():
    """アクティブな全銘柄コード取得の成功ケース"""
    # Arrange
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = [("7203",), ("8306",), ("9432",)]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)

    # Act
    result = await repo.get_all_active_symbols()

    # Assert
    assert result == ["7203", "8306", "9432"]
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_symbols_by_market_success():
    """市場別銘柄コード取得の成功ケース"""
    # Arrange
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = [("7203",), ("8306",)]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)
    market = "プライム"

    # Act
    result = await repo.get_symbols_by_market(market)

    # Assert
    assert result == ["7203", "8306"]
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_symbols_by_sector_success():
    """業種別銘柄コード取得の成功ケース"""
    # Arrange
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = [("7203",), ("6501",)]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)
    sector = "電気機器"

    # Act
    result = await repo.get_symbols_by_sector(sector)

    # Assert
    assert result == ["7203", "6501"]
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_active_symbols_empty_result():
    """アクティブな全銘柄コード取得で空結果の場合"""
    # Arrange
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)

    # Act
    result = await repo.get_all_active_symbols()

    # Assert
    assert result == []
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_symbols_by_market_empty_result():
    """市場別銘柄コード取得で空結果の場合"""
    # Arrange
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)
    market = "スタンダード"

    # Act
    result = await repo.get_symbols_by_market(market)

    # Assert
    assert result == []
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_symbols_by_sector_empty_result():
    """業種別銘柄コード取得で空結果の場合"""
    # Arrange
    mock_session = AsyncMock()
    mock_result = Mock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)
    sector = "銀行業"

    # Act
    result = await repo.get_symbols_by_sector(sector)

    # Assert
    assert result == []
    mock_session.execute.assert_called_once()
