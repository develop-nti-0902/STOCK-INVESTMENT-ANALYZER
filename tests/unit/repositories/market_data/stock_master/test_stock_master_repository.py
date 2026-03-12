"""Unit tests for StockMasterRepository and Master repositories using mocked sessions.

テスト対象：
- MarketCategoryMasterRepository: get_by_code(), get_or_create()
- Sector33MasterRepository: 同様
- Sector17MasterRepository: 同様
- ScaleMasterRepository: 同様
- StockMasterRepository: FK JOIN、eager load、get_by_symbol()、bulk_upsert()
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.stock_master import MarketCategoryMaster, StockMaster
from app.repositories.market_data.stock_master import (
    MarketCategoryMasterRepository,
    Sector33MasterRepository,
    StockMasterRepository,
)

# ============================================================================
# MarketCategoryMasterRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_market_category_master_get_by_code_returns_existing():
    """get_by_code が存在するレコードを取得することを検証する."""
    # Arrange
    mock_session = AsyncMock()
    market_master = MarketCategoryMaster()
    market_master.id = 1
    market_master.code = "Prime"
    market_master.name = "プライム市場"

    # Mock: session.execute を設定
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=market_master)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = MarketCategoryMasterRepository(session=mock_session)

    # Act
    result = await repo.get_by_code("Prime")

    # Assert
    assert result == market_master
    assert result.code == "Prime"


@pytest.mark.asyncio
async def test_market_category_master_get_by_code_returns_none_when_not_found():
    """get_by_code が存在しないレコードに対して None を返すことを検証する."""
    # Arrange
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = MarketCategoryMasterRepository(session=mock_session)

    # Act
    result = await repo.get_by_code("NonExistent")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_market_category_master_get_or_create_returns_existing():
    """get_or_create が存在するレコードを返すことを検証する.

    この場合、新しいレコードは add されない。
    """
    # Arrange
    mock_session = AsyncMock()
    existing = MarketCategoryMaster()
    existing.id = 1
    existing.code = "Prime"
    existing.name = "プライム市場"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=existing)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = MarketCategoryMasterRepository(session=mock_session)

    # Act
    result, created = await repo.get_or_create("Prime", "プライム市場")

    # Assert
    assert result == existing
    assert created is False
    # session.add は呼ばれない
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_market_category_master_get_or_create_creates_new():
    """get_or_create が新しいレコードを作成することを検証する.

    存在しない場合、session.add と session.flush が呼ばれる。
    """
    # Arrange
    mock_session = AsyncMock()

    # 最初の scalar_one_or_none は None を返す（見つからない）
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    repo = MarketCategoryMasterRepository(session=mock_session)

    # Act
    result, created = await repo.get_or_create("Standard", "スタンダード市場")

    # Assert
    assert result.code == "Standard"
    assert result.name == "スタンダード市場"
    assert created is True
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


# ============================================================================
# Sector33MasterRepository Tests (簡易版)
# ============================================================================


@pytest.mark.asyncio
async def test_sector_33_master_get_or_create():
    """Sector33MasterRepository の get_or_create を検証する."""
    # Arrange
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    repo = Sector33MasterRepository(session=mock_session)

    # Act
    result, created = await repo.get_or_create("08", "水産・農林業")

    # Assert
    assert result.code == "08"
    assert result.name == "水産・農林業"
    assert created is True


# ============================================================================
# StockMasterRepository Tests
# ============================================================================


@pytest.mark.asyncio
async def test_stock_master_bulk_upsert_returns_zero_for_empty_records():
    """bulk_upsert が空リストに対して 0 を返すことを検証する."""
    # Arrange
    mock_session = AsyncMock()
    repo = StockMasterRepository(session=mock_session)

    # Act
    result = await repo.bulk_upsert([])

    # Assert
    assert result == 0
    mock_session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_stock_master_bulk_upsert_executes_insert_and_flush():
    """bulk_upsert が execute と flush を呼び出すことを検証する.

    FK ID が設定されたレコードを upsert する想定。
    """
    # Arrange
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()

    repo = StockMasterRepository(session=mock_session)

    records = [
        {
            "stock_code": "1301",
            "stock_name": "極洋",
            "market_category_id": 1,
            "sector_33_id": 2,
            "sector_17_id": 3,
            "scale_id": 4,
            "is_active": 1,
        },
        {
            "stock_code": "1332",
            "stock_name": "日本水産",
            "market_category_id": 1,
            "sector_33_id": 2,
            "sector_17_id": 3,
            "scale_id": 4,
            "is_active": 1,
        },
    ]

    # Act
    result = await repo.bulk_upsert(records)

    # Assert
    assert result == len(records)
    mock_session.execute.assert_awaited()
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_stock_master_get_by_symbol():
    """get_by_symbol が銘柄コードで検索できることを検証する."""
    # Arrange
    mock_session = AsyncMock()
    stock = StockMaster()
    stock.id = 1
    stock.stock_code = "7203"
    stock.stock_name = "Toyota Motor"
    stock.market_category_id = 1
    stock.is_active = 1

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=stock)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)

    # Act
    result = await repo.get_by_symbol("7203")

    # Assert
    assert result == stock
    assert result.stock_code == "7203"


@pytest.mark.asyncio
async def test_stock_master_get_all_active_symbols():
    """get_all_active_symbols がアクティブな銘柄コードリストを返すことを検証する."""
    # Arrange
    mock_session = AsyncMock()

    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[("7203",), ("9202",), ("6758",)])
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = StockMasterRepository(session=mock_session)

    # Act
    result = await repo.get_all_active_symbols()

    # Assert
    assert result == ["7203", "9202", "6758"]
