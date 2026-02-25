"""`StockPriceService` の単体テスト（更新版）.

このファイルは既存テストを全面的に置き換え、最新の `converter` 実装に合わせて
主要パスとエラーハンドリングを検証します.
"""

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from app.exceptions.external_api import YahooFinanceError
from app.services.data_synchronization.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.data_synchronization.market_data.stock_price.saver import StockPriceSaver
from app.services.data_synchronization.market_data.stock_price.service import StockPriceService


class TestStockPriceService:
    """`StockPriceService` の主要フローとエラー処理を検証する."""

    def setup_method(self):
        """Prepare mocked dependencies and the `StockPriceService` instance."""
        self.fetcher = MagicMock(spec=StockPriceFetcher)
        self.saver = MagicMock(spec=StockPriceSaver)
        # saver.session.commit/rollback は await されるため AsyncMock を用意
        session = MagicMock()
        session.commit = AsyncMock(return_value=None)
        session.rollback = AsyncMock(return_value=None)
        self.saver.session = session

        # converter と validator は挙動をテストごとに差し替える
        self.converter = MagicMock()
        self.validator = MagicMock()

        self.service = StockPriceService(
            fetcher=self.fetcher,
            saver=self.saver,
            converter=self.converter,
            validator=self.validator,
        )

    @pytest.mark.asyncio
    async def test_fetch_and_save_single_success(self):
        """Single symbol is fetched, converted and saved successfully."""
        symbol = "7203.T"
        timeframe = "1d"

        # フェッチが返す Pydantic 相当のオブジェクト（model_dump を持つ）
        rec = MagicMock()
        rec.model_dump = MagicMock(
            return_value={"symbol": symbol, "trade_date": "2024-01-01", "close": 100.0}
        )

        self.fetcher.fetch_batch = AsyncMock(return_value={symbol: [rec]})

        # converter.to_saver_records が保存可能な辞書リストを返す
        self.converter.to_saver_records = MagicMock(
            return_value=[{"symbol": symbol, "trade_date": "2024-01-01", "close": 100.0}]
        )

        # バリデータは成功とする
        self.validator.validate = MagicMock(
            return_value=MagicMock(is_valid=True, errors=[], warnings=[])
        )

        # saver が保存件数を返す
        self.saver.save_batch = AsyncMock(return_value=1)

        results = await self.service.fetch_and_save([symbol], timeframe)

        assert isinstance(results, list) and len(results) == 1
        r = results[0]
        assert r.success is True
        assert r.symbol == symbol
        assert r.records_processed == 1
        assert r.records_saved == 1

        # fetcher の呼び出しに symbols と timeframe が含まれていること
        assert self.fetcher.fetch_batch.call_count == 1
        _, kwargs = self.fetcher.fetch_batch.call_args
        assert kwargs.get("symbols") == [symbol]
        assert kwargs.get("timeframe") == timeframe

    @pytest.mark.asyncio
    async def test_fetch_and_save_no_data_returns_warning(self):
        """Empty fetch results produce a successful result with warnings."""
        symbol = "7203.T"
        timeframe = "1d"

        self.fetcher.fetch_batch = AsyncMock(return_value={symbol: []})

        results = await self.service.fetch_and_save([symbol], timeframe)
        r = results[0]

        assert r.success is True
        assert r.records_processed == 0
        assert r.records_saved == 0
        assert r.warnings and isinstance(r.warnings, list)

    @pytest.mark.asyncio
    async def test_fetch_and_save_commit_failure_marks_records_failed(self):
        """Commit failures cause previously successful records to be marked failed."""
        symbol = "7203.T"
        timeframe = "1d"

        rec = MagicMock()
        rec.model_dump = MagicMock(return_value={"symbol": symbol})
        self.fetcher.fetch_batch = AsyncMock(return_value={symbol: [rec]})

        self.converter.to_saver_records = MagicMock(return_value=[{"symbol": symbol}])
        self.validator.validate = MagicMock(
            return_value=MagicMock(is_valid=True, errors=[], warnings=[])
        )
        self.saver.save_batch = AsyncMock(return_value=1)

        # commit が例外を投げる
        self.saver.session.commit = AsyncMock(side_effect=Exception("db commit failed"))

        results = await self.service.fetch_and_save([symbol], timeframe)
        r = results[0]

        assert r.success is False
        assert r.records_saved == 0
        assert any("Commit failed" in e for e in r.errors)

    @pytest.mark.asyncio
    async def test_fetch_and_save_handles_yahoo_error(self):
        """Service returns appropriate errors when YahooFinanceError occurs."""
        symbol = "7203.T"
        timeframe = "1d"

        self.fetcher.fetch_batch = AsyncMock(side_effect=YahooFinanceError())

        results = await self.service.fetch_and_save([symbol], timeframe)
        r = results[0]

        assert r.success is False
        # fetch_batch の外側で例外が起きるとサービスは 'Batch fetch failed' を返す
        assert r.errors and (
            r.errors == ["Batch fetch failed"]
            or any("Yahoo Finance API error" in e for e in r.errors)
        )

    @pytest.mark.asyncio
    async def test_fetch_and_save_batch_fetch_failure(self):
        """When batch fetch fails, each symbol result contains 'Batch fetch failed'."""
        symbols = ["AAA.T", "BBB.T"]
        timeframe = "1d"

        self.fetcher.fetch_batch = AsyncMock(side_effect=Exception("network"))

        results = await self.service.fetch_and_save(symbols, timeframe)

        assert len(results) == 2
        for r in results:
            assert r.success is False
            assert r.errors == ["Batch fetch failed"]

    @pytest.mark.asyncio
    async def test_get_stock_data_returns_dataframe(self):
        """`get_stock_data` returns a wrapper containing a pandas DataFrame."""
        symbol = "7203.T"
        timeframe = "1d"

        rec = MagicMock()
        rec.model_dump = MagicMock(
            return_value={"symbol": symbol, "trade_date": "2024-01-01", "close": 100.0}
        )
        self.fetcher.fetch_batch = AsyncMock(return_value={symbol: [rec]})

        wrapper = await self.service.get_stock_data(symbol, timeframe)

        assert wrapper is not None
        assert wrapper.symbol == symbol
        assert wrapper.timeframe == timeframe
        assert isinstance(wrapper.data, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_get_stock_data_from_db_and_delete_all(self, monkeypatch):
        """Service can read stock data from DB and delete all records for a timeframe."""

        # Fake row object similar to repository row
        class FakeRow:
            def __init__(self, symbol):
                self.symbol = symbol
                self.open = 1.0
                self.high = 2.0
                self.low = 0.5
                self.close = 1.5
                self.volume = 100
                self.adj_close = 1.4
                self.timestamp = None

        # Fake repo to be used in mapping
        class FakeRepo:
            def __init__(self, session=None):
                self._session = session

            async def get_by_symbol_and_range(self, symbol, start, end, limit, offset):
                return [FakeRow(symbol)]

            async def delete_all(self):
                return 5

        # Monkeypatch mapping in service module
        import app.services.data_synchronization.market_data.stock_price.service as svc_mod

        monkeypatch.setitem(svc_mod.TIMEFRAME_REPOSITORY_MAP, "1d", FakeRepo)

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        # call get_stock_data_from_db
        rows = await self.service.get_stock_data_from_db(
            db=mock_db, symbol="7203.T", timeframe="1d"
        )
        assert isinstance(rows, list)
        assert rows[0]["symbol"] == "7203.T"

        # call delete_all_for_timeframe
        deleted = await self.service.delete_all_for_timeframe(db=mock_db, timeframe="1d")
        assert deleted == 5
        mock_db.commit.assert_awaited()
