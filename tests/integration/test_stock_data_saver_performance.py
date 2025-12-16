"""
株価データSaverパフォーマンステスト

大量データを使用して、StockPriceSaverの一括保存パフォーマンスを評価します。
チャンクサイズの最適化と処理時間を計測します。

実装: Issue #115 (パフォーマンス評価)
仕様書: docs/architecture/layers/service_layer.md
"""

import asyncio
import csv
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)


@pytest.fixture
def artifacts_dir():
    """パフォーマンステスト成果物の出力先ディレクトリ"""
    artifacts_path = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_path, exist_ok=True)
    return artifacts_path


def generate_test_dataframe(
    symbol: str, num_records: int, start_date: datetime
) -> pd.DataFrame:
    """テスト用の株価データフレームを生成"""
    timestamps = [
        start_date + timedelta(minutes=i) for i in range(num_records)
    ]
    base_price = 1000.0

    data = {
        "timestamp": timestamps,
        "open": [base_price + (i % 50) for i in range(num_records)],
        "high": [base_price + (i % 50) + 10 for i in range(num_records)],
        "low": [base_price + (i % 50) - 10 for i in range(num_records)],
        "close": [base_price + (i % 50) + 5 for i in range(num_records)],
        "volume": [10000 + (i * 100) for i in range(num_records)],
    }

    return pd.DataFrame(data)


def export_performance_results(results: List[Dict], filepath: str) -> None:
    """パフォーマンス計測結果をCSVにエクスポート"""
    fieldnames = [
        "test_name",
        "batch_size",
        "num_records",
        "num_symbols",
        "timeframe",
        "elapsed_seconds",
        "records_per_second",
        "success",
        "error_message",
    ]

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)

    logger.info(f"Performance results exported to {filepath}")


@pytest.mark.anyio
@pytest.mark.slow
async def test_single_stock_save_performance(monkeypatch, artifacts_dir):
    """
    単一銘柄の大量データ保存パフォーマンステスト

    検証内容:
    - 1000レコード、5000レコード、10000レコードの保存時間を計測
    - バッチサイズ: 1000（デフォルト）
    - タイムフレーム: 1m（1分足）
    """
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"DB接続設定が不足しています: {exc}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    try:
        db_mod.get_session_maker.cache_clear()
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    session_maker = db_mod.get_session_maker()

    test_symbol = "PERF_TEST_1"
    timeframe = "1m"
    start_date = datetime(2024, 1, 1, 9, 0, 0)

    performance_results = []

    # 異なるレコード数でテスト
    for num_records in [1000, 5000, 10000]:
        async with session_maker() as session:
            saver = StockPriceSaver(session, batch_size=1000)

            # テストデータ生成
            df = generate_test_dataframe(test_symbol, num_records, start_date)

            # 保存処理の実行と計測
            start_time = time.time()
            try:
                success = await saver.save_single_stock_data(
                    test_symbol, timeframe, df
                )
                elapsed = time.time() - start_time

                result = {
                    "test_name": "single_stock_save",
                    "batch_size": 1000,
                    "num_records": num_records,
                    "num_symbols": 1,
                    "timeframe": timeframe,
                    "elapsed_seconds": round(elapsed, 3),
                    "records_per_second": (
                        round(num_records / elapsed, 2) if elapsed > 0 else 0
                    ),
                    "success": success,
                    "error_message": None,
                }

                rps = result["records_per_second"]
                perf_msg = (
                    f"Performance: {num_records} records saved in "
                    f"{elapsed:.3f}s ({rps} records/sec)"
                )
                logger.info(perf_msg)

            except Exception as e:
                elapsed = time.time() - start_time
                result = {
                    "test_name": "single_stock_save",
                    "batch_size": 1000,
                    "num_records": num_records,
                    "num_symbols": 1,
                    "timeframe": timeframe,
                    "elapsed_seconds": round(elapsed, 3),
                    "records_per_second": 0,
                    "success": False,
                    "error_message": str(e),
                }
                logger.error(f"Performance test failed: {e}")

            performance_results.append(result)

        # セッション間で少し待機
        await asyncio.sleep(0.5)

    # 結果をエクスポート
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"performance_single_stock_{ts}.csv"
    filepath = os.path.join(artifacts_dir, filename)
    export_performance_results(performance_results, filepath)


@pytest.mark.anyio
@pytest.mark.slow
async def test_batch_size_comparison(monkeypatch, artifacts_dir):
    """
    バッチサイズ別パフォーマンス比較テスト

    検証内容:
    - 同一データ量（5000レコード）を異なるバッチサイズで保存
    - バッチサイズ: 100, 500, 1000, 2000
    - 最適なバッチサイズを特定
    """
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"DB接続設定が不足しています: {exc}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    try:
        db_mod.get_session_maker.cache_clear()
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    session_maker = db_mod.get_session_maker()

    test_symbol = "PERF_TEST_BATCH"
    timeframe = "1m"
    num_records = 5000
    start_date = datetime(2024, 2, 1, 9, 0, 0)

    # テストデータ生成（共通）
    df = generate_test_dataframe(test_symbol, num_records, start_date)

    performance_results = []

    # 異なるバッチサイズでテスト
    for batch_size in [100, 500, 1000, 2000]:
        async with session_maker() as session:
            saver = StockPriceSaver(session, batch_size=batch_size)

            # 保存処理の実行と計測
            start_time = time.time()
            try:
                success = await saver.save_single_stock_data(
                    test_symbol, timeframe, df
                )
                elapsed = time.time() - start_time

                result = {
                    "test_name": "batch_size_comparison",
                    "batch_size": batch_size,
                    "num_records": num_records,
                    "num_symbols": 1,
                    "timeframe": timeframe,
                    "elapsed_seconds": round(elapsed, 3),
                    "records_per_second": (
                        round(num_records / elapsed, 2) if elapsed > 0 else 0
                    ),
                    "success": success,
                    "error_message": None,
                }

                logger.info(
                    f"Batch size {batch_size}: {elapsed:.3f}s "
                    f"({result['records_per_second']} records/sec)"
                )

            except Exception as e:
                elapsed = time.time() - start_time
                result = {
                    "test_name": "batch_size_comparison",
                    "batch_size": batch_size,
                    "num_records": num_records,
                    "num_symbols": 1,
                    "timeframe": timeframe,
                    "elapsed_seconds": round(elapsed, 3),
                    "records_per_second": 0,
                    "success": False,
                    "error_message": str(e),
                }
                logger.error(f"Batch size {batch_size} test failed: {e}")

            performance_results.append(result)

        await asyncio.sleep(0.5)

    # 結果をエクスポート
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"performance_batch_size_comparison_{ts}.csv"
    filepath = os.path.join(artifacts_dir, filename)
    export_performance_results(performance_results, filepath)

    # 最適なバッチサイズを特定
    successful_results = [r for r in performance_results if r["success"]]
    if successful_results:
        best_result = max(
            successful_results, key=lambda x: x["records_per_second"]
        )
        logger.info(
            f"Best batch size: {best_result['batch_size']} "
            f"({best_result['records_per_second']} records/sec)"
        )


@pytest.mark.anyio
@pytest.mark.slow
async def test_multiple_stocks_save_performance(monkeypatch, artifacts_dir):
    """
    複数銘柄の並行保存パフォーマンステスト

    検証内容:
    - 10銘柄、各1000レコードの保存時間を計測
    - 並行処理の効率を検証
    """
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"DB接続設定が不足しています: {exc}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    try:
        db_mod.get_session_maker.cache_clear()
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    session_maker = db_mod.get_session_maker()

    num_symbols = 10
    records_per_symbol = 1000
    timeframe = "1m"
    start_date = datetime(2024, 3, 1, 9, 0, 0)

    # 複数銘柄のデータ準備
    stock_data_dict = {}
    for i in range(num_symbols):
        symbol = f"PERF_MULTI_{i:03d}"
        df = generate_test_dataframe(symbol, records_per_symbol, start_date)
        stock_data_dict[symbol] = {timeframe: df}

    performance_results = []

    async with session_maker() as session:
        saver = StockPriceSaver(session, batch_size=1000)

        # 保存処理の実行と計測
        start_time = time.time()
        try:
            results = await saver.save_batch_stocks(stock_data_dict)
            elapsed = time.time() - start_time

            total_records = num_symbols * records_per_symbol
            total_saved = sum(results.values())

            result = {
                "test_name": "multiple_stocks_save",
                "batch_size": 1000,
                "num_records": total_records,
                "num_symbols": num_symbols,
                "timeframe": timeframe,
                "elapsed_seconds": round(elapsed, 3),
                "records_per_second": (
                    round(total_saved / elapsed, 2) if elapsed > 0 else 0
                ),
                "success": total_saved == total_records,
                "error_message": (
                    None
                    if total_saved == total_records
                    else "Partial save failure"
                ),
            }

            rps_multi = result["records_per_second"]
            multiple_msg = (
                f"Multiple stocks: {num_symbols} symbols, {total_records} "
                f"records in {elapsed:.3f}s ({rps_multi} records/sec)"
            )
            logger.info(multiple_msg)

        except Exception as e:
            elapsed = time.time() - start_time
            result = {
                "test_name": "multiple_stocks_save",
                "batch_size": 1000,
                "num_records": num_symbols * records_per_symbol,
                "num_symbols": num_symbols,
                "timeframe": timeframe,
                "elapsed_seconds": round(elapsed, 3),
                "records_per_second": 0,
                "success": False,
                "error_message": str(e),
            }
            logger.error(f"Multiple stocks test failed: {e}")

        performance_results.append(result)

    # 結果をエクスポート
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"performance_multiple_stocks_{ts}.csv"
    filepath = os.path.join(artifacts_dir, filename)
    export_performance_results(performance_results, filepath)


@pytest.mark.anyio
@pytest.mark.slow
async def test_concurrent_batch_processing(monkeypatch, artifacts_dir):
    """
    並行バッチ処理のパフォーマンステスト

    検証内容:
    - 最大同時実行バッチ数を変更してパフォーマンスを計測
    - max_concurrent_batches: 1, 3, 5
    """
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"DB接続設定が不足しています: {exc}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    try:
        db_mod.get_session_maker.cache_clear()
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    session_maker = db_mod.get_session_maker()

    num_symbols = 5
    records_per_symbol = 2000
    timeframe = "1m"
    start_date = datetime(2024, 4, 1, 9, 0, 0)

    # テストデータ準備
    stock_data_dict = {}
    for i in range(num_symbols):
        symbol = f"PERF_CONCURRENT_{i:03d}"
        df = generate_test_dataframe(symbol, records_per_symbol, start_date)
        stock_data_dict[symbol] = {timeframe: df}

    performance_results = []

    # 異なる並行度でテスト
    for max_concurrent in [1, 3, 5]:
        async with session_maker() as session:
            saver = StockPriceSaver(
                session, batch_size=1000, max_concurrent_batches=max_concurrent
            )

            start_time = time.time()
            try:
                results = await saver.save_batch_stocks(stock_data_dict)
                elapsed = time.time() - start_time

                total_records = num_symbols * records_per_symbol
                total_saved = sum(results.values())

                result = {
                    "test_name": f"concurrent_batches_{max_concurrent}",
                    "batch_size": 1000,
                    "num_records": total_records,
                    "num_symbols": num_symbols,
                    "timeframe": timeframe,
                    "elapsed_seconds": round(elapsed, 3),
                    "records_per_second": (
                        round(total_saved / elapsed, 2) if elapsed > 0 else 0
                    ),
                    "success": total_saved == total_records,
                    "error_message": None,
                }

                logger.info(
                    f"Concurrent batches {max_concurrent}: {elapsed:.3f}s "
                    f"({result['records_per_second']} records/sec)"
                )

            except Exception as e:
                elapsed = time.time() - start_time
                result = {
                    "test_name": f"concurrent_batches_{max_concurrent}",
                    "batch_size": 1000,
                    "num_records": num_symbols * records_per_symbol,
                    "num_symbols": num_symbols,
                    "timeframe": timeframe,
                    "elapsed_seconds": round(elapsed, 3),
                    "records_per_second": 0,
                    "success": False,
                    "error_message": str(e),
                }
                logger.error(f"Concurrent {max_concurrent} test failed: {e}")

            performance_results.append(result)

        await asyncio.sleep(0.5)

    # 結果をエクスポート
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"performance_concurrent_batches_{ts}.csv"
    filepath = os.path.join(artifacts_dir, filename)
    export_performance_results(performance_results, filepath)

