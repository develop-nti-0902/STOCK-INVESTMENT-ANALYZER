"""StockPriceFetcherのユニットテスト

StockPriceFetcherの機能をテストします。
"""

import asyncio
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions.validation import FieldValidationError
from app.schemas.market_data.stock_price import StockData
from app.services.market_data.stock_price.fetcher import (
    StockPriceFetcher,
    TimeframeMapping,
)


class TestTimeframeMapping:
    """TimeframeMapping機能のテストケース"""

    def test_valid_timeframe_conversion(self):
        """有効なタイムフレーム文字列の変換をテスト"""
        # Arrange - 準備
        # 有効なタイムフレーム変換をテスト

        # Act & Assert - 実行と検証
        assert TimeframeMapping.get_yfinance_interval("1d") == "1d"
        assert TimeframeMapping.get_yfinance_interval("1wk") == "1wk"
        assert TimeframeMapping.get_yfinance_interval("1mo") == "1mo"

    def test_invalid_timeframe_conversion(self):
        """無効なタイムフレーム文字列の変換をテスト"""
        # Arrange - 準備
        # 無効なタイムフレーム変換をテスト

        # Act & Assert - 実行と検証
        with pytest.raises(FieldValidationError):
            TimeframeMapping.get_yfinance_interval("invalid")

        with pytest.raises(FieldValidationError):
            TimeframeMapping.get_yfinance_interval("2d")

    def test_get_supported_timeframes(self):
        """サポートされているタイムフレームのリスト取得をテスト"""
        # Arrange - 準備
        # Act - 実行
        supported = TimeframeMapping.get_supported_timeframes()

        # Assert - 検証
        assert isinstance(supported, list)
        assert "1d" in supported
        assert "1wk" in supported
        assert "1mo" in supported

    def test_get_max_period_dates_for_limited_timeframes(self):
        """日数制限のあるタイムフレームの最大期間日付取得をテスト"""
        # Arrange & Act & Assert - 準備、実行、検証
        # Test 1m (7 days)
        start_date, end_date = TimeframeMapping.get_max_period_dates("1m")
        expected_start = date.today() - timedelta(days=7)
        assert start_date == expected_start
        assert end_date is None

        # Test 5m (30 days)
        start_date, end_date = TimeframeMapping.get_max_period_dates("5m")
        expected_start = date.today() - timedelta(days=30)
        assert start_date == expected_start
        assert end_date is None

        # Test 15m (30 days)
        start_date, end_date = TimeframeMapping.get_max_period_dates("15m")
        expected_start = date.today() - timedelta(days=30)
        assert start_date == expected_start
        assert end_date is None

        # Test 30m (30 days)
        start_date, end_date = TimeframeMapping.get_max_period_dates("30m")
        expected_start = date.today() - timedelta(days=30)
        assert start_date == expected_start
        assert end_date is None

        # Test 1h (365 days)
        start_date, end_date = TimeframeMapping.get_max_period_dates("1h")
        expected_start = date.today() - timedelta(days=365)
        assert start_date == expected_start
        assert end_date is None

    def test_get_max_period_dates_for_unlimited_timeframes(self):
        """制限のないタイムフレームの最大期間日付取得をテスト"""
        # Arrange & Act & Assert - 準備、実行、検証
        # Test 1d (max)
        start_date, end_date = TimeframeMapping.get_max_period_dates("1d")
        assert start_date is None
        assert end_date is None

        # Test 1wk (max)
        start_date, end_date = TimeframeMapping.get_max_period_dates("1wk")
        assert start_date is None
        assert end_date is None

        # Test 1mo (max)
        start_date, end_date = TimeframeMapping.get_max_period_dates("1mo")
        assert start_date is None
        assert end_date is None

    def test_get_max_period_dates_invalid_timeframe(self):
        """無効なタイムフレームの最大期間日付取得をテスト"""
        # Arrange - 準備
        # Act & Assert - 実行と検証
        with pytest.raises(FieldValidationError):
            TimeframeMapping.get_max_period_dates("invalid")


class TestStockPriceFetcherMaxPeriod:
    """StockPriceFetcher最大期間機能のテストケース"""

    @pytest.fixture
    def fetcher(self):
        """テスト用のStockPriceFetcherインスタンスを作成"""
        return StockPriceFetcher()

    @pytest.mark.asyncio
    async def test_fetch_single_uses_max_period_for_1m(self, fetcher):
        """fetch_singleが1mタイムフレームで最大期間（7日）を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = [
                StockData(
                    symbol="TEST",
                    trade_date=date.today(),
                    open_price=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000,
                    adj_close=None,
                )
            ]

            # Act - 実行
            result = await fetcher.fetch_single("TEST", timeframe="1m")

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert symbol == "TEST"
            assert interval == "1m"
            assert start_date == date.today() - timedelta(days=7)
            assert end_date is None
            assert timeframe_arg == "1m"
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_fetch_single_uses_max_period_for_5m(self, fetcher):
        """fetch_singleが5mタイムフレームで最大期間（30日）を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act - 実行
            _ = await fetcher.fetch_single("TEST", timeframe="5m")

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert symbol == "TEST"
            assert interval == "5m"
            assert start_date == date.today() - timedelta(days=30)
            assert end_date is None
            assert timeframe_arg == "5m"

    @pytest.mark.asyncio
    async def test_fetch_single_uses_max_period_for_15m(self, fetcher):
        """fetch_singleが15mタイムフレームで最大期間（30日）を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act - 実行
            _ = await fetcher.fetch_single("TEST", timeframe="15m")

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert symbol == "TEST"
            assert interval == "15m"
            assert start_date == date.today() - timedelta(days=30)
            assert end_date is None
            assert timeframe_arg == "15m"

    @pytest.mark.asyncio
    async def test_fetch_single_uses_max_period_for_30m(self, fetcher):
        """fetch_singleが30mタイムフレームで最大期間（30日）を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act - 実行
            _ = await fetcher.fetch_single("TEST", timeframe="30m")

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert symbol == "TEST"
            assert interval == "30m"
            assert start_date == date.today() - timedelta(days=30)
            assert end_date is None
            assert timeframe_arg == "30m"

    @pytest.mark.asyncio
    async def test_fetch_single_uses_max_period_for_1h(self, fetcher):
        """fetch_singleが1hタイムフレームで最大期間（365日）を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act - 実行
            _ = await fetcher.fetch_single("TEST", timeframe="1h")

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert symbol == "TEST"
            assert interval == "1h"
            assert start_date == date.today() - timedelta(days=365)
            assert end_date is None
            assert timeframe_arg == "1h"

    @pytest.mark.asyncio
    async def test_fetch_single_uses_max_period_for_1d(self, fetcher):
        """fetch_singleが1dタイムフレームで最大期間（無制限）を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act - 実行
            _ = await fetcher.fetch_single("TEST", timeframe="1d")

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert symbol == "TEST"
            assert interval == "1d"
            assert start_date is None  # max period
            assert end_date is None
            assert timeframe_arg == "1d"

    @pytest.mark.asyncio
    async def test_fetch_single_respects_explicit_dates(self, fetcher):
        """fetch_singleが明示的に指定された日付を尊重することをテスト"""
        # Arrange - 準備
        custom_start = date(2023, 1, 1)
        custom_end = date(2023, 12, 31)

        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act - 実行
            _ = await fetcher.fetch_single(
                "TEST",
                timeframe="1d",
                start_date=custom_start,
                end_date=custom_end,
            )

            # Assert - 検証
            call_args = mock_fetch.call_args[0]
            symbol, interval, start_date, end_date, timeframe_arg = call_args

            assert start_date == custom_start
            assert end_date == custom_end
            assert timeframe_arg == "1d"

    @pytest.mark.asyncio
    async def test_fetch_batch_uses_max_periods(self, fetcher):
        """fetch_batchが各タイムフレームで最大期間を使用することをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "fetch_single", new_callable=AsyncMock
        ) as mock_fetch_single:
            mock_fetch_single.return_value = []

            symbols = ["TEST1", "TEST2"]

            # Act - 実行
            _ = await fetcher.fetch_batch(symbols, timeframe="5m")

            # Assert - 検証
            # Verify fetch_single was called for each symbol
            assert mock_fetch_single.call_count == 2

            # Check first call
            first_call = mock_fetch_single.call_args_list[0]
            args, kwargs = first_call
            assert kwargs["symbol"] == "TEST1"  # symbol
            assert kwargs["timeframe"] == "5m"
            assert kwargs["start_date"] == date.today() - timedelta(days=30)
            assert kwargs["end_date"] is None


class TestStockPriceFetcherAdditional:
    """StockPriceFetcher追加機能のテストケース"""

    @pytest.fixture
    def fetcher(self):
        """テスト用のStockPriceFetcherインスタンスを作成"""
        return StockPriceFetcher()

    def test_get_period_valid(self):
        """有効なタイムフレームのperiod取得をテスト"""
        # Arrange - 準備
        # Act & Assert - 実行と検証
        assert TimeframeMapping.get_period("1d") == "max"
        assert TimeframeMapping.get_period("1wk") == "max"
        assert TimeframeMapping.get_period("1mo") == "max"
        assert TimeframeMapping.get_period("1m") is None
        assert TimeframeMapping.get_period("5m") is None

    def test_get_period_invalid(self):
        """無効なタイムフレームのperiod取得をテスト"""
        # Arrange - 準備
        # Act & Assert - 実行と検証
        with pytest.raises(FieldValidationError):
            TimeframeMapping.get_period("invalid")

    def test_init(self):
        """StockPriceFetcherの初期化をテスト"""
        # Arrange - 準備
        with patch(
            "app.services.market_data.stock_price.fetcher.get_settings"
        ) as mock_get_settings:
            mock_config = type(
                "Config", (), {"YAHOO_FINANCE_CONCURRENCY_LIMIT": 5}
            )()
            mock_get_settings.return_value = mock_config

            # Act - 実行
            fetcher = StockPriceFetcher()

            # Assert - 検証
            assert fetcher.max_concurrent_requests == 5
            assert isinstance(fetcher.semaphore, asyncio.Semaphore)

    @pytest.mark.asyncio
    async def test_fetch(self, fetcher):
        """fetchメソッドをテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "_fetch_single_symbol", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = [
                StockData(
                    symbol="TEST",
                    trade_date=date.today(),
                    open_price=100.0,
                    high=101.0,
                    low=99.0,
                    close=100.5,
                    volume=1000,
                    adj_close=None,
                )
            ]

            # Act - 実行
            result = await fetcher.fetch("TEST", timeframe="1d")

            # Assert - 検証
            assert len(result) == 1
            assert result[0].symbol == "TEST"
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_invalid_identifier(self, fetcher):
        """fetchメソッドの無効なidentifierテスト"""
        # Arrange - 準備
        # Act & Assert - 実行と検証
        with pytest.raises(FieldValidationError):
            await fetcher.fetch("")

    @pytest.mark.asyncio
    async def test_fetch_batch_with_exceptions(self, fetcher):
        """fetch_batchの例外処理をテスト"""
        # Arrange - 準備
        with patch.object(
            fetcher, "fetch_single", new_callable=AsyncMock
        ) as mock_fetch_single:
            # 最初の呼び出しは成功、2番目は例外
            mock_fetch_single.side_effect = [
                [
                    StockData(
                        symbol="TEST1",
                        trade_date=date.today(),
                        open_price=100.0,
                        high=101.0,
                        low=99.0,
                        close=100.5,
                        volume=1000,
                        adj_close=None,
                    )
                ],
                ValueError("Test error"),
            ]

            symbols = ["TEST1", "TEST2"]

            # Act - 実行
            result = await fetcher.fetch_batch(symbols, timeframe="1d")

            # Assert - 検証
            assert "TEST1" in result
            assert len(result["TEST1"]) == 1
            assert "TEST2" in result
            assert result["TEST2"] == []  # 例外時は空リスト

    def test_parse_yfinance_data(self, fetcher):
        """_parse_yfinance_dataメソッドをテスト"""
        # Arrange - 準備
        import pandas as pd

        data = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1100],
                "Adj Close": [101.0, 102.0],
            },
            index=pd.to_datetime(["2023-01-01", "2023-01-02"]),
        )

        # Act - 実行
        result = fetcher._parse_yfinance_data(data, "TEST")

        # Assert - 検証
        assert len(result) == 2
        assert result[0].symbol == "TEST"
        assert result[0].open_price == 100.0
        assert result[0].close == 101.0
        assert result[1].volume == 1100

    @pytest.mark.asyncio
    async def test_is_valid_symbol_format(self, fetcher):
        """is_valid_symbol_formatメソッドをテスト"""
        # Arrange - 準備
        # Act & Assert - 実行と検証
        # 有効なフォーマット
        assert await fetcher.is_valid_symbol_format("AAPL") is True
        assert await fetcher.is_valid_symbol_format("7203.T") is True
        assert await fetcher.is_valid_symbol_format("0001.HK") is True
        assert await fetcher.is_valid_symbol_format("123") is True

        # 無効なフォーマット
        assert await fetcher.is_valid_symbol_format("aapl") is False  # 小文字
        assert (
            await fetcher.is_valid_symbol_format("AAPL$") is False
        )  # 特殊文字
        assert (
            await fetcher.is_valid_symbol_format("AAPL.") is False
        )  # ドットのみ
        assert await fetcher.is_valid_symbol_format("") is False  # 空文字列
        assert await fetcher.is_valid_symbol_format(None) is False  # None

    @pytest.mark.asyncio
    async def test_handle_fetch_error(self, fetcher):
        """handle_fetch_errorメソッドをテスト"""
        # Arrange - 準備
        from app.exceptions.external_api import YahooFinanceError

        # Act & Assert - 実行と検証
        # YahooFinanceErrorの場合
        yahoo_error = YahooFinanceError(message="Test Yahoo error")
        await fetcher.handle_fetch_error("TEST", yahoo_error)

        # 一般的な例外の場合
        general_error = ValueError("Test general error")
        await fetcher.handle_fetch_error("TEST", general_error)

    @pytest.mark.asyncio
    async def test_fetch_single_symbol_with_period(self, fetcher):
        """_fetch_single_symbolがperiodを使用する場合をテスト"""
        # Arrange - 準備
        from unittest.mock import patch as mock_patch

        import pandas as pd

        with mock_patch("yfinance.Ticker") as mock_ticker:
            mock_instance = mock_ticker.return_value
            mock_hist = pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [101.0],
                    "Low": [99.0],
                    "Close": [100.5],
                    "Volume": [1000],
                },
                index=pd.to_datetime(["2023-01-01"]),
            )
            mock_instance.history.return_value = mock_hist

            # Act - 実行
            result = await fetcher._fetch_single_symbol(
                "TEST", "1d", None, None, "1d"
            )

            # Assert - 検証
            assert len(result) == 1
            mock_instance.history.assert_called_with(
                period="max",
                interval="1d",
                prepost=False,
                actions=False,
            )

    @pytest.mark.asyncio
    async def test_fetch_single_symbol_with_start_end(self, fetcher):
        """_fetch_single_symbolがstart/endを使用する場合をテスト"""
        # Arrange - 準備
        from unittest.mock import patch as mock_patch

        import pandas as pd

        with mock_patch("yfinance.Ticker") as mock_ticker:
            mock_instance = mock_ticker.return_value
            mock_hist = pd.DataFrame(
                {
                    "Open": [100.0],
                    "High": [101.0],
                    "Low": [99.0],
                    "Close": [100.5],
                    "Volume": [1000],
                },
                index=pd.to_datetime(["2023-01-01"]),
            )
            mock_instance.history.return_value = mock_hist

            start_date = date(2023, 1, 1)
            end_date = date(2023, 12, 31)

            # Act - 実行
            result = await fetcher._fetch_single_symbol(
                "TEST", "1m", start_date, end_date, "1m"
            )

            # Assert - 検証
            assert len(result) == 1
            mock_instance.history.assert_called_with(
                interval="1m",
                start=start_date,
                end=end_date,
                prepost=False,
                actions=False,
            )

    @pytest.mark.asyncio
    async def test_fetch_multi_yfinance(self, fetcher):
        """fetch_multi_yfinance が複数銘柄を正しくパースすることをテスト"""
        from unittest.mock import patch as mock_patch

        import pandas as pd

        with mock_patch("yfinance.Tickers") as mock_tickers:
            mock_instance = mock_tickers.return_value

            # MultiIndex columns: (attribute, ticker)
            cols = pd.MultiIndex.from_tuples(
                [
                    ("Open", "AAPL"),
                    ("High", "AAPL"),
                    ("Low", "AAPL"),
                    ("Close", "AAPL"),
                    ("Volume", "AAPL"),
                    ("Open", "7203.T"),
                    ("High", "7203.T"),
                    ("Low", "7203.T"),
                    ("Close", "7203.T"),
                    ("Volume", "7203.T"),
                ]
            )

            data = [
                [
                    100.0,
                    101.0,
                    99.0,
                    100.5,
                    1000,
                    200.0,
                    201.0,
                    199.0,
                    200.5,
                    2000,
                ]
            ]

            df = pd.DataFrame(
                data, index=pd.to_datetime(["2023-01-01"]), columns=cols
            )

            mock_instance.history.return_value = df

            result = await fetcher.fetch_multi_yfinance(
                ["AAPL", "7203"], timeframe="1d"
            )

            assert "AAPL" in result
            assert "7203" in result
            assert len(result["AAPL"]) == 1
            assert len(result["7203"]) == 1
            assert result["AAPL"][0].symbol == "AAPL"
            assert result["7203"][0].symbol == "7203"
            assert result["AAPL"][0].open_price == 100.0
            assert result["7203"][0].open_price == 200.0

    def test_parse_yfinance_data_with_missing_columns(self, fetcher):
        """_parse_yfinance_dataが欠損列を扱う場合をテスト"""
        # Arrange - 準備
        import pandas as pd

        # Adj Close が欠損
        data = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2023-01-01"]),
        )

        # Act - 実行
        result = fetcher._parse_yfinance_data(data, "TEST")

        # Assert - 検証
        assert len(result) == 1
        assert result[0].adj_close is None

    def test_parse_yfinance_data_with_validation_error(self, fetcher):
        """_parse_yfinance_dataのValidationErrorをテスト"""
        # Arrange - 準備
        import numpy as np
        import pandas as pd

        # NaN値を含むデータ
        data = pd.DataFrame(
            {
                "Open": [np.nan],  # NaN
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
                "Volume": [1000],
                "Adj Close": [101.0],
            },
            index=pd.to_datetime(["2023-01-01"]),
        )

        # Act - 実行
        result = fetcher._parse_yfinance_data(data, "TEST")

        # Assert - 検証
        # NaNはNoneに変換されるので、成功する
        assert len(result) == 1
        assert result[0].open_price is None

    @pytest.mark.asyncio
    async def test_handle_fetch_error_with_yahoo_error(self, fetcher):
        """handle_fetch_errorがYahooFinanceErrorをログに記録することをテスト"""
        # Arrange - 準備
        from app.exceptions.external_api import YahooFinanceError

        with patch(
            "app.services.market_data.stock_price.fetcher.logger"
        ) as mock_logger:
            error = YahooFinanceError(message="Yahoo API error")

            # Act - 実行
            await fetcher.handle_fetch_error("TEST", error)

            # Assert - 検証
            # YahooFinanceErrorの場合はerrorとwarningの両方が呼ばれる
            mock_logger.error.assert_called_with(
                f"Error fetching data for TEST: {error}"
            )
            mock_logger.warning.assert_called_with(
                f"Yahoo Finance API error for TEST: {error}"
            )

    @pytest.mark.asyncio
    async def test_handle_fetch_error_with_general_error(self, fetcher):
        """handle_fetch_errorが一般的なエラーをログに記録することをテスト"""
        # Arrange - 準備
        with patch(
            "app.services.market_data.stock_price.fetcher.logger"
        ) as mock_logger:
            error = ValueError("General error")

            # Act - 実行
            await fetcher.handle_fetch_error("TEST", error)

            # Assert - 検証
            mock_logger.error.assert_called_with(
                f"Unexpected error for TEST: {error}"
            )
            mock_logger.warning.assert_not_called()
