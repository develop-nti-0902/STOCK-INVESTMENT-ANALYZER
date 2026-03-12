"""`StockMasterSaver` の単体テスト.

テスト内容:
 - save_with_masters(): 完全フロー（マスター作成 > FK変換 > upsert）を検証
 - save_with_masters(): FK参照への変換が正しいこと
 - save_with_masters(): 空の stocks リストでも動作すること
 - save_with_masters(): 存在しないマスター値への対応（None ID）
 - save_with_masters(): 例外発生時のロールバック
"""

from unittest.mock import AsyncMock

import pytest

from app.schemas.market_data.stock_master import StockMasterNormalized
from app.services.data_synchronization.market_data.stock_master.saver import StockMasterSaver

# ============================================================================
# Tests for save_with_masters() - New Normalization Method
# ============================================================================


@pytest.mark.asyncio
async def test_save_with_masters_returns_zero_for_empty_stocks():
    """save_with_masters() が空の stocks リストで 0 を返すことを検証する."""
    # Mock stock master repository
    mock_stock_repo = AsyncMock()
    mock_stock_repo.session = AsyncMock()
    mock_stock_repo.delete_all = AsyncMock()
    mock_stock_repo.bulk_upsert = AsyncMock(return_value=0)

    # Create saver
    saver = StockMasterSaver(stock_master_repo=mock_stock_repo, batch_size=10)

    # Mock master repositories with tuple return values
    mock_market = AsyncMock()
    mock_market.id = 1
    saver.market_repo = AsyncMock()
    saver.market_repo.get_or_create = AsyncMock(return_value=(mock_market, True))

    mock_sector_33 = AsyncMock()
    mock_sector_33.id = 2
    saver.sector_33_repo = AsyncMock()
    saver.sector_33_repo.get_or_create = AsyncMock(return_value=(mock_sector_33, True))

    mock_sector_17 = AsyncMock()
    mock_sector_17.id = 3
    saver.sector_17_repo = AsyncMock()
    saver.sector_17_repo.get_or_create = AsyncMock(return_value=(mock_sector_17, True))

    mock_scale = AsyncMock()
    mock_scale.id = 4
    saver.scale_repo = AsyncMock()
    saver.scale_repo.get_or_create = AsyncMock(return_value=(mock_scale, True))

    # Test data: 空の stocks
    data_dict = {
        "market_categories": {"Prime": "プライム市場"},
        "sector_33": {"08": "水産・農林業"},
        "sector_17": {"1": "水産物・農産物"},
        "scale": {"L": "Large"},
        "stocks": [],  # 空
    }

    # Execute
    result = await saver.save_with_masters(data_dict)

    # Assert: 0 を返す
    assert result == 0
    mock_stock_repo.delete_all.assert_awaited()


@pytest.mark.asyncio
async def test_save_with_masters_converts_fk_references_correctly():
    """save_with_masters() が FK 参照への変換を正しく実行することを検証する."""
    # Setup: Mock stock master repository
    mock_stock_repo = AsyncMock()
    mock_stock_repo.session = AsyncMock()
    mock_stock_repo.delete_all = AsyncMock()
    mock_stock_repo.bulk_upsert = AsyncMock(return_value=1)

    # Create saver
    saver = StockMasterSaver(stock_master_repo=mock_stock_repo, batch_size=10)

    # Create mock master objects with proper structure
    mock_market = AsyncMock()
    mock_market.id = 1
    mock_market.code = "Prime"
    mock_market.name = "プライム市場"

    mock_sector_33 = AsyncMock()
    mock_sector_33.id = 2
    mock_sector_33.code = "08"
    mock_sector_33.name = "水産・農林業"

    mock_sector_17 = AsyncMock()
    mock_sector_17.id = 3
    mock_sector_17.code = "1"
    mock_sector_17.name = "水産物・農産物"

    mock_scale = AsyncMock()
    mock_scale.id = 4
    mock_scale.code = "L"
    mock_scale.name = "Large"

    # Mock master repositories with tuple return values
    saver.market_repo = AsyncMock()
    saver.market_repo.get_or_create = AsyncMock(return_value=(mock_market, True))

    saver.sector_33_repo = AsyncMock()
    saver.sector_33_repo.get_or_create = AsyncMock(return_value=(mock_sector_33, True))

    saver.sector_17_repo = AsyncMock()
    saver.sector_17_repo.get_or_create = AsyncMock(return_value=(mock_sector_17, True))

    saver.scale_repo = AsyncMock()
    saver.scale_repo.get_or_create = AsyncMock(return_value=(mock_scale, True))

    # Test data with StockMasterNormalized objects
    stock = StockMasterNormalized(
        stock_code="1301",
        stock_name="極洋",
        market_category="Prime",
        sector_code_33="08",
        sector_code_17="1",
        scale_code="L",
        data_date="20251209",
        is_active=1,
    )

    data_dict = {
        "market_categories": {"Prime": "プライム市場"},
        "sector_33": {"08": "水産・農林業"},
        "sector_17": {"1": "水産物・農産物"},
        "scale": {"L": "Large"},
        "stocks": [stock],
    }

    # Execute
    result = await saver.save_with_masters(data_dict)

    # Assert
    assert result == 1
    mock_stock_repo.delete_all.assert_awaited_once()
    mock_stock_repo.bulk_upsert.assert_awaited_once()

    # Check the bulk_upsert call
    call_args = mock_stock_repo.bulk_upsert.call_args
    records = call_args[0][0]  # First argument (records list)

    assert len(records) == 1
    assert records[0]["stock_code"] == "1301"
    assert records[0]["stock_name"] == "極洋"
    assert records[0]["market_category_id"] == 1
    assert records[0]["sector_33_id"] == 2
    assert records[0]["sector_17_id"] == 3
    assert records[0]["scale_id"] == 4
    assert records[0]["data_date"] == "20251209"
    assert records[0]["is_active"] == 1


@pytest.mark.asyncio
async def test_save_with_masters_handles_missing_masters():
    """save_with_masters() が存在しないマスターに対して None ID で処理することを検証する."""
    # Setup: Mock stock master repository
    mock_stock_repo = AsyncMock()
    mock_stock_repo.session = AsyncMock()
    mock_stock_repo.delete_all = AsyncMock()
    mock_stock_repo.bulk_upsert = AsyncMock(return_value=1)

    # Create saver
    saver = StockMasterSaver(stock_master_repo=mock_stock_repo, batch_size=10)

    # Mock: マスターを見つけられない場合（タプル形式で None を返す）
    saver.market_repo = AsyncMock()
    saver.market_repo.get_or_create = AsyncMock(return_value=(None, False))

    saver.sector_33_repo = AsyncMock()
    saver.sector_33_repo.get_or_create = AsyncMock(return_value=(None, False))

    saver.sector_17_repo = AsyncMock()
    saver.sector_17_repo.get_or_create = AsyncMock(return_value=(None, False))

    saver.scale_repo = AsyncMock()
    saver.scale_repo.get_or_create = AsyncMock(return_value=(None, False))

    # Test data
    stock = StockMasterNormalized(
        stock_code="9999",
        stock_name="Unknown",
        market_category="Unknown",
        sector_code_33="99",
        sector_code_17="99",
        scale_code="X",
        data_date="20251209",
        is_active=1,
    )

    data_dict = {
        "market_categories": {"Unknown": "Unknown"},
        "sector_33": {"99": "Unknown"},
        "sector_17": {"99": "Unknown"},
        "scale": {"X": "Unknown"},
        "stocks": [stock],
    }

    # Execute
    result = await saver.save_with_masters(data_dict)

    # Assert
    assert result == 1
    call_args = mock_stock_repo.bulk_upsert.call_args
    records = call_args[0][0]

    assert records[0]["market_category_id"] is None
    assert records[0]["sector_33_id"] is None
    assert records[0]["sector_17_id"] is None
    assert records[0]["scale_id"] is None


@pytest.mark.asyncio
async def test_save_with_masters_handles_exception_and_rollback():
    """save_with_masters() が例外発生時にロールバックすることを検証する."""
    # Setup: Mock stock master repository that throws error
    mock_stock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_stock_repo.session = mock_session
    mock_stock_repo.delete_all = AsyncMock(side_effect=RuntimeError("DB Error"))

    # Create saver
    saver = StockMasterSaver(stock_master_repo=mock_stock_repo, batch_size=10)

    # Mock master repositories with get_or_create returning tuples
    mock_market = AsyncMock()
    mock_market.id = 1
    saver.market_repo = AsyncMock()
    saver.market_repo.get_or_create = AsyncMock(return_value=(mock_market, True))

    mock_sector_33 = AsyncMock()
    mock_sector_33.id = 2
    saver.sector_33_repo = AsyncMock()
    saver.sector_33_repo.get_or_create = AsyncMock(return_value=(mock_sector_33, True))

    mock_sector_17 = AsyncMock()
    mock_sector_17.id = 3
    saver.sector_17_repo = AsyncMock()
    saver.sector_17_repo.get_or_create = AsyncMock(return_value=(mock_sector_17, True))

    mock_scale = AsyncMock()
    mock_scale.id = 4
    saver.scale_repo = AsyncMock()
    saver.scale_repo.get_or_create = AsyncMock(return_value=(mock_scale, True))

    data_dict = {
        "market_categories": {"Prime": "プライム市場"},
        "sector_33": {"08": "水産・農林業"},
        "sector_17": {"1": "水産物・農産物"},
        "scale": {"L": "Large"},
        "stocks": [],
    }

    # Execute: 例外が発生する想定
    with pytest.raises(RuntimeError):
        await saver.save_with_masters(data_dict)

    # Assert: ロールバックが呼ばれたこと
    mock_session.rollback.assert_awaited_once()
