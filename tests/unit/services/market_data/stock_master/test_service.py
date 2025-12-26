"""
StockMasterService単体テスト

銘柄マスタサービス（オーケストレーション層）の機能をテストします。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master.fetcher import StockMasterFetcher
from app.services.market_data.stock_master.service import StockMasterService


class TestStockMasterService:
    """StockMasterServiceのテストクラス"""

    def setup_method(self):
        """テスト前準備"""
        # モックの作成
        self.mock_repo = MagicMock(spec=StockMasterRepository)
        self.mock_fetcher = MagicMock(spec=StockMasterFetcher)

        # Serviceインスタンス作成
        self.service = StockMasterService(
            repo=self.mock_repo,
            fetcher=self.mock_fetcher,
        )

    @pytest.mark.asyncio
    async def test_get_all_active_symbols_success(self):
        """全アクティブ銘柄取得の成功ケース"""
        # テストデータ
        expected_symbols = ["7203", "8306", "9432"]

        # モックの設定
        self.mock_repo.get_all_active_symbols = AsyncMock(
            return_value=expected_symbols
        )

        # テスト実行
        result = await self.service.get_all_active_symbols()

        # 検証
        assert result == expected_symbols
        self.mock_repo.get_all_active_symbols.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_active_symbols_failure(self):
        """全アクティブ銘柄取得の失敗ケース"""
        # モックの設定
        self.mock_repo.get_all_active_symbols = AsyncMock(
            side_effect=Exception("DB error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="DB error"):
            await self.service.get_all_active_symbols()

    @pytest.mark.asyncio
    async def test_get_symbols_by_market_success(self):
        """市場別銘柄取得の成功ケース"""
        # テストデータ
        market = "プライム"
        expected_symbols = ["7203", "8306"]

        # モックの設定
        self.mock_repo.get_symbols_by_market = AsyncMock(
            return_value=expected_symbols
        )

        # テスト実行
        result = await self.service.get_symbols_by_market(market)

        # 検証
        assert result == expected_symbols
        self.mock_repo.get_symbols_by_market.assert_called_once_with(market)

    @pytest.mark.asyncio
    async def test_get_symbols_by_market_failure(self):
        """市場別銘柄取得の失敗ケース"""
        # テストデータ
        market = "プライム"

        # モックの設定
        self.mock_repo.get_symbols_by_market = AsyncMock(
            side_effect=Exception("DB error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="DB error"):
            await self.service.get_symbols_by_market(market)

    @pytest.mark.asyncio
    async def test_get_symbols_by_sector_success(self):
        """業種別銘柄取得の成功ケース"""
        # テストデータ
        sector = "電気機器"
        expected_symbols = ["7203", "6501"]

        # モックの設定
        self.mock_repo.get_symbols_by_sector = AsyncMock(
            return_value=expected_symbols
        )

        # テスト実行
        result = await self.service.get_symbols_by_sector(sector)

        # 検証
        assert result == expected_symbols
        self.mock_repo.get_symbols_by_sector.assert_called_once_with(sector)

    @pytest.mark.asyncio
    async def test_get_symbols_by_sector_failure(self):
        """業種別銘柄取得の失敗ケース"""
        # テストデータ
        sector = "電気機器"

        # モックの設定
        self.mock_repo.get_symbols_by_sector = AsyncMock(
            side_effect=Exception("DB error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="DB error"):
            await self.service.get_symbols_by_sector(sector)

    @pytest.mark.asyncio
    async def test_refresh_stock_master_success(self):
        """銘柄マスタ更新の成功ケース"""
        # テストデータ
        expected_count = 100

        # モックの設定
        self.service.fetch_and_store = AsyncMock(return_value=expected_count)

        # テスト実行
        result = await self.service.refresh_stock_master()

        # 検証
        assert result == expected_count
        self.service.fetch_and_store.assert_called_once_with(source="jpx")

    @pytest.mark.asyncio
    async def test_refresh_stock_master_failure(self):
        """銘柄マスタ更新の失敗ケース"""
        # モックの設定
        self.service.fetch_and_store = AsyncMock(
            side_effect=Exception("Fetch error")
        )

        # テスト実行と検証
        with pytest.raises(Exception, match="Fetch error"):
            await self.service.refresh_stock_master()


# fetch_and_store メソッドのテスト
@pytest.mark.asyncio
async def test_fetch_and_store_calls_repo_bulk_upsert():
    """fetch_and_storeがリポジトリのbulk_upsertを適切に呼び出すことを確認"""
    # Arrange: モックのフェッチャーが2件返すようにする
    from app.schemas.market_data.stock_master import StockMasterNormalized

    mock_item_1 = StockMasterNormalized(
        stock_code="1301",
        stock_name="Test Co",
        market_category="Prime",
    )
    mock_item_2 = StockMasterNormalized(
        stock_code="1332",
        stock_name="Test2 Co",
        market_category="Prime",
    )

    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[mock_item_1, mock_item_2])

    mock_repo = AsyncMock()

    # Arrange: bulk_upsert は受け取った件数を返すように設定
    async def fake_bulk_upsert(records):
        return len(records)

    mock_repo.bulk_upsert = AsyncMock(side_effect=fake_bulk_upsert)

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act: 実行
    processed = await service.fetch_and_store("jpx", batch_size=1)

    # Assert: 2レコード処理されるはず
    assert processed == 2
    # Assert: bulk_upsert は 2 回（バッチサイズ1で2回）呼ばれている
    assert mock_repo.bulk_upsert.call_count == 2


@pytest.mark.asyncio
async def test_fetch_and_store_unsupported_source_raises():
    """未対応のソース名でValueErrorが発生することを確認"""
    # Arrange
    mock_repo = AsyncMock()
    service = StockMasterService(repo=mock_repo, fetcher=AsyncMock())

    # Act / Assert: 未対応のソース名で ValueError が発生する
    with pytest.raises(ValueError):
        await service.fetch_and_store("unsupported")


@pytest.mark.asyncio
async def test_fetch_and_store_fetcher_error_propagates():
    """フェッチャーのエラーが適切に伝搬することを確認"""
    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(side_effect=RuntimeError("fetch fail"))
    mock_repo = AsyncMock()

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: フェッチ時の例外が伝搬する
    with pytest.raises(RuntimeError):
        await service.fetch_and_store("jpx")


@pytest.mark.asyncio
async def test_fetch_and_store_repo_error_propagates():
    """リポジトリのエラーが適切に伝搬することを確認"""
    from app.schemas.market_data.stock_master import StockMasterNormalized

    # valid pydantic items
    item = StockMasterNormalized(
        stock_code="1301",
        stock_name="Test Co",
    )
    # Arrange
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[item])

    mock_repo = AsyncMock()
    mock_repo.bulk_upsert = AsyncMock(side_effect=RuntimeError("db error"))

    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: リポジトリ側の例外が伝搬する
    with pytest.raises(RuntimeError):
        await service.fetch_and_store("jpx")


@pytest.mark.asyncio
async def test_fetch_and_store_invalid_item_type_raises():
    """不正な型のアイテムでTypeErrorが発生することを確認"""
    # Arrange: フェッチャーが dict を返す（不正な型）
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_all = AsyncMock(return_value=[{"code": "1301"}])

    mock_repo = AsyncMock()
    service = StockMasterService(repo=mock_repo, fetcher=mock_fetcher)

    # Act / Assert: Pydantic モデルではないアイテムで TypeError
    with pytest.raises(TypeError):
        await service.fetch_and_store("jpx")
