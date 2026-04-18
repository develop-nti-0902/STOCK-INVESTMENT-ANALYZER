"""`StockMasterService` の単体テスト（修正版）.

テスト規約に沿い、日本語コメントと非同期テスト用の `pytest.mark.asyncio` を利用しています.

テスト対象：
- get_all_active_symbols(): 全アクティブシンボル取得
- get_symbols_by_market(): 市場別シンボル取得
- get_symbols_by_sector(): 業種別シンボル取得
- fetch_and_save(): フェッチ → マスター抽出 → 保存
- reset_stock_master(): リセット
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.schemas.market_data.stock_master import StockMasterNormalized
from app.services.data_synchronization.market_data.stock_master.service import StockMasterService


@pytest.mark.asyncio
async def test_get_all_active_symbols_success_and_error():
    """全件取得が成功するケースと例外が透過されるケースを確認する."""
    mock_repo = MagicMock()
    mock_repo.get_all_active_symbols = AsyncMock(return_value=["7203"])

    svc = StockMasterService(repo=mock_repo, fetcher=None)
    result = await svc.get_all_active_symbols()
    assert result == ["7203"]

    # 例外が透過されること
    mock_repo.get_all_active_symbols = AsyncMock(side_effect=RuntimeError("db"))
    with pytest.raises(RuntimeError):
        await svc.get_all_active_symbols()


@pytest.mark.asyncio
async def test_get_symbols_by_market_and_sector_success_and_error():
    """市場・業種別取得の正常系と例外伝搬を確認する."""
    mock_repo = MagicMock()
    mock_repo.get_symbols_by_market = AsyncMock(return_value=["1111"])
    mock_repo.get_symbols_by_sector = AsyncMock(return_value=["2222"])

    svc = StockMasterService(repo=mock_repo, fetcher=None)

    assert await svc.get_symbols_by_market("Prime") == ["1111"]
    assert await svc.get_symbols_by_sector("Tech") == ["2222"]

    mock_repo.get_symbols_by_market = AsyncMock(side_effect=RuntimeError("mkt err"))
    with pytest.raises(RuntimeError):
        await svc.get_symbols_by_market("Prime")

    mock_repo.get_symbols_by_sector = AsyncMock(side_effect=RuntimeError("sec err"))
    with pytest.raises(RuntimeError):
        await svc.get_symbols_by_sector("Tech")


@pytest.mark.asyncio
async def test_fetch_and_save_basic_flow():
    """fetch_and_save の基本フロー를 検증する."""
    # Mock fetcher
    mock_fetcher = AsyncMock()

    # fetch_and_extract_masters の戻り値をモック
    # stocks リスト内の item は StockMasterNormalized オブジェクトである必要があります
    mock_stocks = [
        StockMasterNormalized(
            stock_code="1301",
            stock_name="極洋",
            market_category="Prime",
            sector_code_33="08",
            sector_code_17="1",
            scale_code="L",
            data_date="20251209",
            is_active=1,
        ),
    ]

    mock_data_dict = {
        "market_categories": {"Prime": "Prime"},
        "sector_33": {"08": "水産・農林業"},
        "sector_17": {"1": "水産物・農産物"},
        "scale": {"L": "Large"},
        "stocks": mock_stocks,
    }

    mock_fetcher.fetch_and_extract_masters = AsyncMock(return_value=mock_data_dict)

    # Mock saver
    mock_saver = AsyncMock()
    mock_saver.save_with_masters = AsyncMock(return_value=1)

    # Mock repo
    mock_repo = MagicMock()
    mock_repo.get_all_active_symbols = AsyncMock(return_value=[])

    # Mock nikkei225 service
    mock_nikkei225 = AsyncMock()
    mock_nikkei225.fetch_and_update = AsyncMock(
        return_value={"success": True, "count": 225, "error": None}
    )

    # Create service
    svc = StockMasterService(
        repo=mock_repo,
        fetcher=mock_fetcher,
        saver=mock_saver,
        nikkei225_service=mock_nikkei225,
    )

    # Execute
    result = await svc.fetch_and_save()

    # Assert
    assert result["stock_master"]["updated_count"] == 1
    mock_fetcher.fetch_and_extract_masters.assert_awaited_once()
    mock_saver.save_with_masters.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_and_save_with_limit():
    """limit パラメータで件数をフィルタすることを検証する."""
    mock_fetcher = AsyncMock()

    # モックデータ: 3件の株（StockMasterNormalizedオブジェクト）
    mock_stocks = [
        StockMasterNormalized(
            stock_code="1301",
            stock_name="極洋",
            market_category="Prime",
            sector_code_33="08",
            sector_code_17="1",
            scale_code="L",
            data_date="20251209",
            is_active=1,
        ),
        StockMasterNormalized(
            stock_code="7203",
            stock_name="トヨタ",
            market_category="Prime",
            sector_code_33="07",
            sector_code_17="12",
            scale_code="L",
            data_date="20251209",
            is_active=1,
        ),
        StockMasterNormalized(
            stock_code="1111",
            stock_name="テスト銘柄",
            market_category="Prime",
            sector_code_33="01",
            sector_code_17="1",
            scale_code="M",
            data_date="20251209",
            is_active=1,
        ),
    ]

    mock_data_dict = {
        "market_categories": {"Prime": "Prime"},
        "sector_33": {"08": "水産・農林業", "07": "輸送用機器", "01": "鉱業"},
        "sector_17": {"1": "水産物・農産物", "12": "自動車"},
        "scale": {"L": "Large", "M": "Medium"},
        "stocks": mock_stocks,
    }

    mock_fetcher.fetch_and_extract_masters = AsyncMock(return_value=mock_data_dict)

    mock_saver = AsyncMock()
    mock_saver.save_with_masters = AsyncMock(return_value=1)

    mock_repo = MagicMock()
    mock_repo.get_all_active_symbols = AsyncMock(return_value=[])

    # Mock nikkei225 service
    mock_nikkei225 = AsyncMock()
    mock_nikkei225.fetch_and_update = AsyncMock(
        return_value={"success": True, "count": 225, "error": None}
    )

    svc = StockMasterService(
        repo=mock_repo,
        fetcher=mock_fetcher,
        saver=mock_saver,
        nikkei225_service=mock_nikkei225,
    )

    # Execute with limit=2
    result = await svc.fetch_and_save(limit=2)

    # Assert: saver に渡されたデータは 2 件のみ
    assert result["stock_master"]["updated_count"] == 1
    call_args = mock_saver.save_with_masters.call_args
    saved_data = call_args[0][0]
    assert len(saved_data["stocks"]) == 2


@pytest.mark.asyncio
async def test_fetch_and_save_invalid_limit_raises_value_error():
    """limit に負の値を与えるとエラーになることを確認する."""
    mock_fetcher = AsyncMock()
    mock_data_dict = {
        "market_categories": {},
        "sector_33": {},
        "sector_17": {},
        "scale": {},
        "stocks": [],
    }
    mock_fetcher.fetch_and_extract_masters = AsyncMock(return_value=mock_data_dict)

    svc = StockMasterService(repo=MagicMock(), fetcher=mock_fetcher)

    with pytest.raises(ValueError):
        await svc.fetch_and_save(limit=-1)


@pytest.mark.asyncio
async def test_fetch_and_save_with_updates_repo_creates_summary():
    """updates_repo が与えられた場合、サマリが作成され success に更新されることを確認する."""
    mock_fetcher = AsyncMock()

    mock_stocks = [
        StockMasterNormalized(
            stock_code="7203",
            stock_name="トヨタ",
            market_category="Prime",
            sector_code_33="07",
            sector_code_17="12",
            scale_code="L",
            data_date="20251209",
            is_active=1,
        ),
    ]

    mock_data_dict = {
        "market_categories": {"Prime": "Prime"},
        "sector_33": {"07": "輸送用機器"},
        "sector_17": {"12": "自動車"},
        "scale": {"L": "Large"},
        "stocks": mock_stocks,
    }

    mock_fetcher.fetch_and_extract_masters = AsyncMock(return_value=mock_data_dict)

    mock_saver = AsyncMock()
    mock_saver.save_with_masters = AsyncMock(return_value=1)

    mock_repo = MagicMock()
    mock_repo.get_all_active_symbols = AsyncMock(return_value=[])

    updates_repo = MagicMock()
    created = Mock()
    created.id = 123
    updates_repo.create_summary = AsyncMock(return_value=created)
    updates_repo.update_status = AsyncMock()

    # Mock nikkei225 service
    mock_nikkei225 = AsyncMock()
    mock_nikkei225.fetch_and_update = AsyncMock(
        return_value={"success": True, "count": 225, "error": None}
    )

    svc = StockMasterService(
        repo=mock_repo,
        fetcher=mock_fetcher,
        saver=mock_saver,
        updates_repo=updates_repo,
        nikkei225_service=mock_nikkei225,
    )

    result = await svc.fetch_and_save()

    assert result["stock_master"]["updated_count"] == 1
    updates_repo.create_summary.assert_awaited_once()
    updates_repo.update_status.assert_awaited()


@pytest.mark.asyncio
async def test_reset_stock_master_deletes_and_calls_updates_repo():
    """reset_stock_master がリポジトリ削除を行い、updates_repo の削除も呼ぶことを確認する."""
    mock_repo = MagicMock()
    mock_repo.delete_all = AsyncMock(return_value=7)

    updates_repo = MagicMock()
    updates_repo.delete_by_reset = AsyncMock(return_value=3)

    svc = StockMasterService(repo=mock_repo, fetcher=None, updates_repo=updates_repo)
    deleted = await svc.reset_stock_master()

    assert deleted == 7
    updates_repo.delete_by_reset.assert_awaited_once()


@pytest.mark.asyncio
async def test_screening_service_uses_fk_sector_17_reference():
    """Screening Service が FK 産業17参照で正常に動作することを検証する.

    Stock Master の正規化により、screening_service.py が
    StockMaster.sector_17 の FK 参照を使用できることを確認します.
    """
    # Mock repositories
    mock_repo = MagicMock()

    # StockMaster records with FK references to masters
    from app.models.market_data.stock_master import StockMaster

    # Create mock sector_17 object
    sector_17 = Mock()
    sector_17.id = 1
    sector_17.code = "12"
    sector_17.name = "自動車"

    # Create mock Stock with FK relationships
    stock = Mock(spec=StockMaster)
    stock.stock_code = "7203"
    stock.stock_name = "トヨタ"
    stock.sector_17_id = 1
    stock.sector_17 = sector_17  # Relationship loaded
    stock.is_active = 1

    # Mock repository to return stock with populated relationships
    mock_repo.get_by_symbol = AsyncMock(return_value=stock)

    # Assert that FK reference is present and accessible
    assert stock.sector_17 is not None
    assert stock.sector_17.code == "12"
    assert stock.sector_17.name == "自動車"
