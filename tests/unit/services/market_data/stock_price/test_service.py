"""
StockPriceService単体テスト

株価データサービス（オーケストレーション層）の機能をテストします。
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.service import (
    StockPriceService,
    StockPriceServiceResult,
)
from app.services.market_data.stock_price.validator import StockPriceValidator


class TestStockPriceService:
    """StockPriceServiceのテストクラス"""

    def setup_method(self):
        """テスト前準備"""
        # モックの作成
        self.mock_fetcher = MagicMock(spec=StockPriceFetcher)
        self.mock_saver = MagicMock(spec=StockPriceSaver)
        self.mock_converter = MagicMock(spec=StockPriceConverter)
        self.mock_validator = MagicMock(spec=StockPriceValidator)

        # Serviceインスタンス作成
        self.service = StockPriceService(
            fetcher=self.mock_fetcher,
            saver=self.mock_saver,
            converter=self.mock_converter,
            validator=self.mock_validator,
            max_concurrent=2,
        )

    @pytest.mark.asyncio
    async def test_fetch_and_save_single_success(self):
        """単一銘柄処理の成功ケース"""
        # テストデータ
        symbol = "7203.T"
        timeframe = "1d"
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # モックの戻り値設定
        mock_stock_data_list = [
            MagicMock(
                symbol=symbol,
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                model_dump=MagicMock(
                    return_value={
                        "symbol": symbol,
                        "trade_date": datetime(
                            2024, 1, 1, tzinfo=timezone.utc
                        ),
                        "close": 102.0,
                    }
                ),
            ),
            MagicMock(
                symbol=symbol,
                trade_date=datetime(2024, 1, 2, tzinfo=timezone.utc),
                model_dump=MagicMock(
                    return_value={
                        "symbol": symbol,
                        "trade_date": datetime(
                            2024, 1, 2, tzinfo=timezone.utc
                        ),
                        "close": 103.0,
                    }
                ),
            ),
        ]

        # mock_pydantic_data is not required in this test

        mock_dict_data = [
            {
                "symbol": symbol,
                "trade_date": datetime(2024, 1, 1, tzinfo=timezone.utc),
            },
            {
                "symbol": symbol,
                "trade_date": datetime(2024, 1, 2, tzinfo=timezone.utc),
            },
        ]

        # モック設定
        self.mock_fetcher.fetch_single = AsyncMock(
            return_value=mock_stock_data_list
        )
        self.mock_validator.validate = MagicMock(
            return_value=MagicMock(is_valid=True, errors=[], warnings=[])
        )
        self.mock_converter.from_pydantic = MagicMock(
            side_effect=mock_dict_data
        )
        self.mock_saver.save_batch = AsyncMock(return_value=2)

        # テスト実行
        result = await self.service.fetch_and_save_single(
            symbol, timeframe, start_date, end_date
        )

        # 検証
        assert result.success is True
        assert result.symbol == symbol
        assert result.timeframe == timeframe
        assert result.records_processed == 2
        assert result.records_saved == 2
        assert len(result.errors) == 0

        # モック呼び出し検証
        self.mock_fetcher.fetch_single.assert_called_once_with(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )
        assert self.mock_validator.validate.call_count == 2
        assert self.mock_converter.from_pydantic.call_count == 2
        self.mock_saver.save_batch.assert_called_once_with(mock_dict_data)

    @pytest.mark.asyncio
    async def test_fetch_and_save_single_no_data(self):
        """データが取得できないケース"""
        symbol = "7203.T"
        timeframe = "1d"

        # 空のリストを返す
        self.mock_fetcher.fetch_single = AsyncMock(return_value=[])

        result = await self.service.fetch_and_save_single(
            symbol, timeframe, date(2024, 1, 1), date(2024, 1, 31)
        )

        assert result.success is True
        assert result.records_processed == 0
        assert result.records_saved == 0
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_fetch_and_save_single_validation_failure(self):
        """検証失敗のケース"""
        symbol = "7203.T"
        timeframe = "1d"

        mock_stock_data_list = [
            MagicMock(
                symbol=symbol,
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                model_dump=MagicMock(
                    return_value={
                        "symbol": symbol,
                        "trade_date": datetime(
                            2024, 1, 1, tzinfo=timezone.utc
                        ),
                        "close": 102.0,
                    }
                ),
            ),
        ]

        mock_pydantic_data = [MagicMock()]

        self.mock_fetcher.fetch_single = AsyncMock(
            return_value=mock_stock_data_list
        )
        self.mock_converter.from_dataframe = MagicMock(
            return_value=mock_pydantic_data
        )
        self.mock_validator.validate = MagicMock(
            return_value=MagicMock(is_valid=False, errors=["Validation error"])
        )

        result = await self.service.fetch_and_save_single(
            symbol, timeframe, date(2024, 1, 1), date(2024, 1, 31)
        )

        assert result.success is False
        assert result.records_processed == 1
        assert result.records_saved == 0
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_fetch_and_save_multiple_success(self):
        """複数銘柄処理の成功ケース"""
        symbols = ["7203.T", "6758.T"]
        timeframe = "1d"

        # 各銘柄の結果をモック
        mock_result1 = StockPriceServiceResult(
            success=True,
            symbol="7203.T",
            timeframe=timeframe,
            records_processed=2,
            records_saved=2,
        )
        mock_result2 = StockPriceServiceResult(
            success=True,
            symbol="6758.T",
            timeframe=timeframe,
            records_processed=2,
            records_saved=2,
        )

        # fetch_and_save_singleをモック
        self.service.fetch_and_save_single = AsyncMock(
            side_effect=[mock_result1, mock_result2]
        )

        results = await self.service.fetch_and_save_multiple(
            symbols, timeframe, date(2024, 1, 1), date(2024, 1, 31)
        )

        assert len(results) == 2
        assert all(r.success for r in results)
        assert all(r.records_saved == 2 for r in results)

        # 並列呼び出しを検証
        assert self.service.fetch_and_save_single.call_count == 2

    @pytest.mark.asyncio
    async def test_get_stock_data_success(self):
        """データ取得（読み取り専用）の成功ケース"""
        symbol = "7203.T"
        timeframe = "1d"

        mock_stock_data_list = [
            MagicMock(
                symbol=symbol,
                trade_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
                model_dump=MagicMock(
                    return_value={
                        "symbol": symbol,
                        "trade_date": datetime(
                            2024, 1, 1, tzinfo=timezone.utc
                        ),
                        "close": 100.0,
                    }
                ),
            ),
        ]

        self.mock_fetcher.fetch_single = AsyncMock(
            return_value=mock_stock_data_list
        )

        result = await self.service.get_stock_data(
            symbol, timeframe, date(2024, 1, 1), date(2024, 1, 31)
        )

        assert result is not None
        assert result.symbol == symbol
        assert result.timeframe == timeframe
        self.mock_fetcher.fetch_single.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_data_failure(self):
        """データ取得失敗のケース"""
        symbol = "7203.T"
        timeframe = "1d"

        self.mock_fetcher.fetch_single = AsyncMock(
            side_effect=Exception("API Error")
        )

        result = await self.service.get_stock_data(
            symbol, timeframe, date(2024, 1, 1), date(2024, 1, 31)
        )

        assert result is None
