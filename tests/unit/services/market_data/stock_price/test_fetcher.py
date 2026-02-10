"""`StockPriceFetcher` の単体テスト（書き直し）。

テストは簡潔に、命名規約に従い、
`app.services.market_data.stock_price.fetcher` の公開振る舞いを検証します。
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.exceptions.validation import FieldValidationError
from app.schemas.market_data.stock_price import StockData
from app.services.market_data.stock_price.fetcher import StockPriceFetcher, TimeframeMapping


class TestTimeframeMapping:
    # タイムフレーム → yfinance interval の正しい変換を確認
    def test_get_yfinance_interval_valid(self):
        assert TimeframeMapping.get_yfinance_interval("1d") == "1d"
        assert TimeframeMapping.get_yfinance_interval("1m") == "1m"

    def test_get_yfinance_interval_invalid(self):
        with pytest.raises(FieldValidationError):
            TimeframeMapping.get_yfinance_interval("invalid")

    def test_get_supported_timeframes(self):
        # サポートされているタイムフレーム一覧を取得して確認
        supported = TimeframeMapping.get_supported_timeframes()
        assert isinstance(supported, list)
        assert "1d" in supported

    def test_get_period_valid_and_invalid(self):
        assert TimeframeMapping.get_period("1m") == "7d"
        assert TimeframeMapping.get_period("1d") == "max"
        with pytest.raises(FieldValidationError):
            TimeframeMapping.get_period("bogus")


class TestStockPriceFetcherUnit:
    @pytest.fixture
    def fetcher(self):
        # テスト用の StockPriceFetcher インスタンスを返すフィクスチャ
        return StockPriceFetcher()

    def test_init_reads_settings_concurrency(self):
        with patch(
            "app.services.market_data.stock_price.fetcher.get_settings"
        ) as mock_get_settings:
            mock_cfg = type("Cfg", (), {"YAHOO_FINANCE_CONCURRENCY_LIMIT": 3})()
            mock_get_settings.return_value = mock_cfg
            f = StockPriceFetcher()
            assert f.max_concurrent_requests == 3
            assert isinstance(f.semaphore, asyncio.Semaphore)

    @pytest.mark.asyncio
    async def test_fetch_batch_validates_symbols(self, fetcher):
        # 空リストはバリデーションエラーになる
        with pytest.raises(FieldValidationError):
            await fetcher.fetch_batch([], timeframe="1d")

    @pytest.mark.asyncio
    async def test_fetch_batch_delegates_to_internal(self, fetcher):
        # 内部の一括取得メソッドへ委譲していることを確認
        with patch.object(fetcher, "_fetch_multi_symbol", new_callable=AsyncMock) as mock_multi:
            mock_multi.return_value = {
                "T": [StockData(symbol="T", timestamp=datetime.now(timezone.utc))]
            }
            res = await fetcher.fetch_batch(["T"], timeframe="1d")
            mock_multi.assert_awaited()
            assert "T" in res

    def test_parse_yfinance_data_basic(self, fetcher):
        # 基本的なDataFrameからStockDataへ正しく変換されることを確認
        df = pd.DataFrame(
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

        out = fetcher._parse_yfinance_data(df, "TEST")
        assert len(out) == 2
        assert all(isinstance(x, StockData) for x in out)
        assert out[0].symbol == "TEST"
        assert out[0].open_price == 100.0
        assert out[1].volume == 1100

    def test_parse_yfinance_data_missing_adj(self, fetcher):
        # Adj Close 列がない場合は adj_close が None になることを確認
        df = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
                "Volume": [1000],
            },
            index=pd.to_datetime(["2023-01-01"]),
        )
        out = fetcher._parse_yfinance_data(df, "TEST")
        assert len(out) == 1
        assert out[0].adj_close is None

    @pytest.mark.asyncio
    async def test_is_valid_symbol_format(self, fetcher):
        # シンボル形式の検証（有効／無効ケース）
        assert await fetcher.is_valid_symbol_format("AAPL") is True
        assert await fetcher.is_valid_symbol_format("7203.T") is True
        assert await fetcher.is_valid_symbol_format("0001.HK") is True
        assert await fetcher.is_valid_symbol_format("123") is True

        assert await fetcher.is_valid_symbol_format("aapl") is False
        assert await fetcher.is_valid_symbol_format("AAPL$") is False
        assert await fetcher.is_valid_symbol_format("") is False
        assert await fetcher.is_valid_symbol_format(None) is False

    @pytest.mark.asyncio
    async def test_handle_fetch_error_logs(self, fetcher):
        from app.exceptions.external_api import YahooFinanceError

        # YahooFinanceError の場合は error/warning が呼ばれる
        with patch("app.services.market_data.stock_price.fetcher.logger") as mock_logger:
            err = YahooFinanceError(message="err")
            await fetcher.handle_fetch_error("T", err)
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()

        # 一般的な例外の場合は error のみ呼ばれる
        with patch("app.services.market_data.stock_price.fetcher.logger") as mock_logger:
            err = ValueError("boom")
            await fetcher.handle_fetch_error("T", err)
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_fetch_batch_with_yfinance_multiindex(self, fetcher):
        # yfinance の MultiIndex 戻り値を模擬して複数銘柄の解析を検証
        with patch("app.services.market_data.stock_price.fetcher.yf.Tickers") as mock_tickers:
            inst = mock_tickers.return_value

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

            data = [[100.0, 101.0, 99.0, 100.5, 1000, 200.0, 201.0, 199.0, 200.5, 2000]]
            df = pd.DataFrame(data, index=pd.to_datetime(["2023-01-01"]), columns=cols)

            inst.history.return_value = df

            res = await fetcher.fetch_batch(["AAPL", "7203"], timeframe="1d")
            assert "AAPL" in res
            assert "7203" in res
