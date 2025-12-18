"""
StockPriceService統合テスト

株価データ収集サービスの統合動作をテストします。
"""

from datetime import date

import pytest

from app.services.market_data.stock_price import (
    StockPriceConverter,
    StockPriceFetcher,
    StockPriceSaver,
    StockPriceService,
    StockPriceValidator,
)


class TestStockPriceServiceIntegration:
    """StockPriceServiceの統合テスト"""

    def setup_method(self):
        """テスト前準備"""
        self.fetcher = StockPriceFetcher()
        self.converter = StockPriceConverter()
        self.validator = StockPriceValidator()
        # saverはDBセッションが必要なので、テストDBを使用

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """サービスの初期化テスト"""
        from unittest.mock import MagicMock

        mock_saver = MagicMock(spec=StockPriceSaver)
        service = StockPriceService(
            fetcher=self.fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
        )

        assert service.fetcher is self.fetcher
        assert service.saver is mock_saver
        assert service.converter is self.converter
        assert service.validator is self.validator
        assert service.max_concurrent == 5  # デフォルト値

    @pytest.mark.asyncio
    async def test_converter_integration(self):
        """Converterの統合テスト"""
        # テストデータ作成
        import pandas as pd

        df = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [95.0, 96.0],
                "Close": [102.0, 103.0],
                "Volume": [1000000, 1100000],
                "Adj Close": [102.0, 103.0],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        # Converterで変換
        pydantic_data = self.converter.from_dataframe(
            df=df, symbol="7203.T", timeframe="1d"
        )

        assert len(pydantic_data) == 2

        # Validatorで検証
        for item in pydantic_data:
            result = self.validator.validate(item)
            assert result.is_valid, f"Validation failed: {result.errors}"

        # Dict変換
        dict_data = [
            self.converter.from_pydantic(item) for item in pydantic_data
        ]
        assert len(dict_data) == 2
        assert all(isinstance(d, dict) for d in dict_data)
        assert all("symbol" in d for d in dict_data)

    @pytest.mark.asyncio
    async def test_validator_comprehensive(self):
        """Validatorの包括的テスト"""
        from datetime import datetime, timezone

        from app.schemas.stock_data import StockPriceCreate

        # 有効なデータ
        valid_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
        )

        result = self.validator.validate(valid_data)
        assert result.is_valid is True

        # 無効なデータ（OHLC整合性違反）
        invalid_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            open_price=110.0,  # 高値より高い
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000000,
        )

        result = self.validator.validate(invalid_data)
        assert result.is_valid is False
        assert any(
            "Open price must be within the range" in error
            for error in result.errors
        )

    # 注意: 実際のAPI呼び出しを含むテストは、モックを使用するか、
    # テスト環境でのみ実行するように設計する必要があります。
    # 以下のテストはモックを使用した例です。

    @pytest.mark.asyncio
    async def test_service_workflow_simulation(self):
        """サービスワークフローのシミュレーションテスト"""
        # このテストでは実際のAPIを呼ばずに、モックデータを使用
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock

        # モックデータ作成 - List[StockData]として
        from app.schemas.market_data.stock_price import StockData

        mock_stock_data_list = [
            StockData(
                symbol="7203.T",
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                open_price=100.0,
                high=105.0,
                low=95.0,
                close=102.0,
                volume=1000000,
                adj_close=102.0,
            )
        ]

        # Fetcherをモック
        mock_fetcher = MagicMock(spec=StockPriceFetcher)
        mock_fetcher.fetch_single = AsyncMock(
            return_value=mock_stock_data_list
        )

        # Saverをモック（実際のDB保存を避ける）
        mock_saver = MagicMock(spec=StockPriceSaver)
        mock_saver.save_batch = AsyncMock(return_value=1)

        # Service作成
        service = StockPriceService(
            fetcher=mock_fetcher,
            saver=mock_saver,
            converter=self.converter,
            validator=self.validator,
        )

        # テスト実行
        result = await service.fetch_and_save_single(
            symbol="7203.T",
            timeframe="1d",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        # 検証
        assert result.success is True
        assert result.symbol == "7203.T"
        assert result.records_processed == 1
        assert result.records_saved == 1

        # 各コンポーネントが呼ばれたことを確認
        mock_fetcher.fetch_single.assert_called_once()
        mock_saver.save_batch.assert_called_once()
