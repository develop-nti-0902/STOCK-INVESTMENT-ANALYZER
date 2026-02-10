"""`StockPriceBatchRunner` の単体テスト。

テスト方針: 外部依存（BatchExecutionContext, StockMasterService, StockPriceService）をモック化して
`execute_jpx_all_for_timeframe` の分岐（例外、成功、失敗、進捗更新）を検証します。
"""

import asyncio
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from app.services.market_data.stock_price.batch import StockPriceBatchRunner


class DummyCtx:
    def __init__(self):
        self.progress_updates: List[Dict[str, Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def update_progress(self, **kwargs):
        self.progress_updates.append(kwargs)


def test_run_raises_without_stock_master_service():
    runner = StockPriceBatchRunner(
        batch_service=object(), stock_price_service=None, stock_master_service=None
    )

    with pytest.raises(RuntimeError):
        asyncio.run(runner.execute_jpx_all_for_timeframe(timeframe="1d"))


def test_run_processes_symbols_and_updates_progress(monkeypatch):
    # サービスのセットアップ
    symbols = ["AAA", "BBB", "CCC", "DDD"]

    async def get_all_active_symbols():
        return symbols

    class DummyStockMaster:
        async def get_all_active_symbols(self):
            return await get_all_active_symbols()

    # fetch_and_save はチャンクごとに呼ばれ、結果リストを返す想定
    async def fetch_and_save(chunk, timeframe: str, period=None):
        # 結果のミックスを生成: None（成功扱い）、成功オブジェクト、失敗オブジェクト
        results = []
        for s in chunk:
            if s.endswith("A"):
                results.append(None)
            elif s.endswith("B"):
                results.append(SimpleNamespace(success=True, symbol=s, errors=None))
            else:
                results.append(SimpleNamespace(success=False, symbol=s, errors=["err"]))
        return results

    stock_price_service = SimpleNamespace(fetch_and_save=fetch_and_save)

    batch_service = object()

    # run() 内で使用される BatchExecutionContext を monkeypatch する
    # 対象モジュールが存在することを確認して BatchExecutionContext をパッチ
    import importlib

    be_module = importlib.import_module("app.services.batch.batch_execution_service")
    dummy_ctx = DummyCtx()

    class DummyBatchExecutionContext:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return dummy_ctx

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(be_module, "BatchExecutionContext", DummyBatchExecutionContext)

    runner = StockPriceBatchRunner(
        batch_service=batch_service,
        stock_price_service=stock_price_service,
        stock_master_service=DummyStockMaster(),
    )

    # 小さい batch_size で複数チャンクに分割されることを確認して実行
    summary = asyncio.run(runner.execute_jpx_all_for_timeframe(timeframe="1d", batch_size=2))

    assert summary["total"] == len(symbols)
    # マッピング: 'AAA' -> None（成功）, 'BBB' -> success True, その他 -> 失敗
    # したがって 4 銘柄では AAA(success), BBB(success), CCC(failed), DDD(failed)
    assert summary["success"] == 2
    assert summary["failed"] == 2
    assert isinstance(summary["errors"], list)

    # ダミーコンテキストに進捗更新が記録されたことを検証
    assert len(dummy_ctx.progress_updates) >= 1
