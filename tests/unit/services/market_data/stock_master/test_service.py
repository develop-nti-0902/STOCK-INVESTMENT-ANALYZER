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
