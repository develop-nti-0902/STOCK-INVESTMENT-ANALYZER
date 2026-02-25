"""Unit tests for `StockPriceBatchRunner` behavior."""

from types import SimpleNamespace

import pytest

from app.services.data_synchronization.market_data.stock_price.batch import StockPriceBatchRunner


class DummyStockPriceService:
    """テスト用のダミー株価サービス."""

    async def fetch_and_save(self, chunk, timeframe=None, period=None):
        """チャンクを受け取り成功結果を返すダミー実装."""
        return [SimpleNamespace(success=True, symbol=s, errors=None) for s in chunk]


class DummyStockMasterService:
    """テスト用のダミー銘柄マスタサービス."""

    async def get_all_active_symbols(self):
        """アクティブシンボルのリストを返すダミー実装."""
        return ["AAA", "BBB"]


@pytest.mark.asyncio
async def test_execute_jpx_all_for_timeframe_success():
    """全銘柄バッチが正常に成功/失敗数を集計することを確認する."""
    runner = StockPriceBatchRunner(
        stock_price_service=DummyStockPriceService(),
        stock_master_service=DummyStockMasterService(),
    )

    res = await runner.execute_jpx_all_for_timeframe("1d", batch_size=10)
    assert res["total"] == 2
    assert res["success"] == 2
    assert res["failed"] == 0


@pytest.mark.asyncio
async def test_execute_jpx_all_for_timeframe_missing_master_raises():
    """`stock_master_service` が無い場合に RuntimeError が発生することを確認する."""
    runner = StockPriceBatchRunner(
        stock_price_service=DummyStockPriceService(),
        stock_master_service=None,
    )

    with pytest.raises(RuntimeError):
        await runner.execute_jpx_all_for_timeframe("1d")
