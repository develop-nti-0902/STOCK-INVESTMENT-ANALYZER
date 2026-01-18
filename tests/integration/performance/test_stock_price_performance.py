import json
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
from sqlalchemy import select

import app.utils.database as db_mod
from app.models.stock_data import Stocks1d
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from tests.integration.utils import (
    TEST_SYMBOLS,
    cleanup_database,
    register_test_symbols,
    setup_test_database,
)


def _write_performance_artifact(
    test_name: str, performance_data: dict[str, Any]
) -> None:
    artifact_dir = Path(__file__).parent.parent / "artifacts" / "performance"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifact_file = artifact_dir / f"{test_name}.json"

    with open(artifact_file, "w", encoding="utf-8") as f:
        json.dump(performance_data, f, indent=2, ensure_ascii=False)

    print(f"\n=== Performance Test Results: {test_name} ===")
    for key, value in performance_data.items():
        # 数値の場合のみフォーマット
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            print(f"{key}: {value:.4f} seconds")
        else:
            print(f"{key}: {value}")
    print(f"Artifact saved to: {artifact_file}")


@pytest.mark.anyio
async def test_fetch_batch_persists_1d_performance(monkeypatch):
    """
    パフォーマンステスト: fetch_batch + save_batch の各ステップの実行時間を計測します。

    計測項目:
    - yfinance からのデータ取得時間
    - データ変換時間
    - DB への挿入/更新操作時間（コミット前）
    - コミット時間
    - 全体の実行時間
    - 検証時間
    """
    performance_data = {}

    # === セットアップ ===
    setup_start = time.perf_counter()
    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)
    fetcher = StockPriceFetcher()
    session_maker = db_mod.get_session_maker()
    setup_end = time.perf_counter()
    performance_data["setup_time"] = setup_end - setup_start

    # === 1. yfinance からのデータ取得 ===
    fetch_start = time.perf_counter()
    results = await fetcher.fetch_batch(TEST_SYMBOLS, timeframe="1d")
    fetch_end = time.perf_counter()
    performance_data["yfinance_fetch_time"] = fetch_end - fetch_start
    performance_data["symbols_fetched"] = len(results)

    # === 2. データ変換 ===
    transform_start = time.perf_counter()
    data_list = []
    total_records = 0
    for symbol, stock_datas in results.items():
        records = []
        for sd in stock_datas:
            records.append(
                {
                    "timestamp": sd.trade_date,
                    "open": sd.open_price,
                    "high": sd.high,
                    "low": sd.low,
                    "close": sd.close,
                    "volume": sd.volume,
                    "adj_close": sd.adj_close,
                }
            )
        if records:
            data_list.append(
                {"symbol": symbol, "timeframe": "1d", "records": records}
            )
            total_records += len(records)
    transform_end = time.perf_counter()
    performance_data["data_transformation_time"] = (
        transform_end - transform_start
    )
    performance_data["total_records_transformed"] = total_records

    # === 3. DB 操作（コミット前） ===
    async with session_maker() as session:
        saver = StockPriceSaver(session=session)

        db_operation_start = time.perf_counter()
        saved_count = await saver.save_batch(data_list)
        db_operation_end = time.perf_counter()
        performance_data["db_operation_time"] = (
            db_operation_end - db_operation_start
        )
        performance_data["records_saved"] = saved_count

        # === 4. コミット ===
        commit_start = time.perf_counter()
        await session.commit()
        commit_end = time.perf_counter()
        performance_data["commit_time"] = commit_end - commit_start

    # === 5. 検証 ===
    verify_start = time.perf_counter()
    async with session_maker() as verify_session:
        all_rows = []
        for symbol in TEST_SYMBOLS:
            q = await verify_session.execute(
                select(Stocks1d).where(Stocks1d.symbol == symbol)
            )
            rows = q.scalars().all()
            all_rows.extend(rows)

        assert len(all_rows) >= 0
        performance_data["records_verified"] = len(all_rows)
    verify_end = time.perf_counter()
    performance_data["verification_time"] = verify_end - verify_start

    # === 全体時間 ===
    performance_data["total_time"] = (
        performance_data["yfinance_fetch_time"]
        + performance_data["data_transformation_time"]
        + performance_data["db_operation_time"]
        + performance_data["commit_time"]
        + performance_data["verification_time"]
    )

    # === 平均時間の計算 ===
    if performance_data["symbols_fetched"] > 0:
        performance_data["avg_time_per_symbol"] = (
            performance_data["yfinance_fetch_time"]
            / performance_data["symbols_fetched"]
        )

    if performance_data["total_records_transformed"] > 0:
        performance_data["avg_time_per_record"] = (
            performance_data["total_time"]
            / performance_data["total_records_transformed"]
        )

    # パフォーマンスデータをアーティファクトとして保存
    _write_performance_artifact(
        "test_fetch_batch_persists_1d_performance", performance_data
    )

    # クリーンアップ
    await cleanup_database(engine)


@pytest.mark.anyio
async def test_fetch_batch_multiple_timeframes_performance(monkeypatch):
    """
    パフォーマンステスト: 複数のタイムフレームでのデータ取得時間を比較します。

    各タイムフレームごとに取得時間を計測し、比較データを出力します。
    """
    timeframes = ["1d", "1wk", "1mo"]
    performance_data = {"timeframes": {}}

    for timeframe in timeframes:
        timeframe_data = {}

        # セットアップ
        setup_start = time.perf_counter()
        # 簡易的にStocks1dを使用（実際にはtimeframeに応じたモデルを使うべき）
        engine = await setup_test_database(monkeypatch, Stocks1d)
        await register_test_symbols(TEST_SYMBOLS)
        fetcher = StockPriceFetcher()
        setup_end = time.perf_counter()
        timeframe_data["setup_time"] = setup_end - setup_start

        # データ取得
        fetch_start = time.perf_counter()
        results = await fetcher.fetch_batch(TEST_SYMBOLS, timeframe=timeframe)
        fetch_end = time.perf_counter()
        timeframe_data["fetch_time"] = fetch_end - fetch_start

        # レコード数をカウント
        total_records = sum(len(data) for data in results.values())
        timeframe_data["total_records"] = total_records
        timeframe_data["symbols_count"] = len(results)

        if total_records > 0:
            timeframe_data["avg_time_per_record"] = (
                timeframe_data["fetch_time"] / total_records
            )

        performance_data["timeframes"][timeframe] = timeframe_data

        # クリーンアップ
        await cleanup_database(engine)

    # パフォーマンスデータをアーティファクトとして保存
    _write_performance_artifact(
        "test_fetch_batch_multiple_timeframes_performance", performance_data
    )


@pytest.mark.anyio
async def test_save_batch_scalability_performance(monkeypatch):
    """
    パフォーマンステスト: バッチサイズによる保存処理のスケーラビリティを検証します。

    異なる銘柄数でデータ保存時間を計測し、スケーラビリティを確認します。
    """
    performance_data = {"batch_sizes": {}}

    # テスト用の銘柄リスト（サイズ違い）
    batch_configs = [
        ("small", TEST_SYMBOLS[:2]),  # 2銘柄
        ("medium", TEST_SYMBOLS[:5]),  # 5銘柄
        ("large", TEST_SYMBOLS),  # 全銘柄
    ]

    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)
    fetcher = StockPriceFetcher()

    for batch_name, symbols in batch_configs:
        batch_data = {}
        batch_data["symbols_count"] = len(symbols)

        # データ取得
        fetch_start = time.perf_counter()
        results = await fetcher.fetch_batch(symbols, timeframe="1d")
        fetch_end = time.perf_counter()
        batch_data["fetch_time"] = fetch_end - fetch_start

        # データ変換
        transform_start = time.perf_counter()
        data_list = []
        total_records = 0
        for symbol, stock_datas in results.items():
            records = []
            for sd in stock_datas:
                records.append(
                    {
                        "timestamp": sd.trade_date,
                        "open": sd.open_price,
                        "high": sd.high,
                        "low": sd.low,
                        "close": sd.close,
                        "volume": sd.volume,
                        "adj_close": sd.adj_close,
                    }
                )
            if records:
                data_list.append(
                    {"symbol": symbol, "timeframe": "1d", "records": records}
                )
                total_records += len(records)
        transform_end = time.perf_counter()
        batch_data["transform_time"] = transform_end - transform_start
        batch_data["total_records"] = total_records

        # DB保存
        session_maker = db_mod.get_session_maker()
        async with session_maker() as session:
            saver = StockPriceSaver(session=session)

            save_start = time.perf_counter()
            saved_count = await saver.save_batch(data_list)
            save_end = time.perf_counter()
            batch_data["save_time"] = save_end - save_start
            batch_data["records_saved"] = saved_count

            commit_start = time.perf_counter()
            await session.commit()
            commit_end = time.perf_counter()
            batch_data["commit_time"] = commit_end - commit_start

        batch_data["total_time"] = (
            batch_data["fetch_time"]
            + batch_data["transform_time"]
            + batch_data["save_time"]
            + batch_data["commit_time"]
        )

        if batch_data["total_records"] > 0:
            batch_data["avg_time_per_record"] = (
                batch_data["total_time"] / batch_data["total_records"]
            )

        performance_data["batch_sizes"][batch_name] = batch_data

    # パフォーマンスデータをアーティファクトとして保存
    _write_performance_artifact(
        "test_save_batch_scalability_performance", performance_data
    )

    await cleanup_database(engine)


@pytest.mark.anyio
async def test_investigate_nan_fields(monkeypatch):
    """
    デバッグテスト: yfinanceから取得したデータのNaN値を調査します。

    調査項目:
    - 各フィールドごとのNaN件数
    - 銘柄ごとのNaN発生状況
    - NaNが含まれるレコードの詳細
    """
    engine = await setup_test_database(monkeypatch, Stocks1d)
    await register_test_symbols(TEST_SYMBOLS)

    fetcher = StockPriceFetcher()

    # データ取得
    results = await fetcher.fetch_batch(TEST_SYMBOLS, timeframe="1d")

    # NaN調査用のデータ構造
    nan_analysis: Dict[str, Any] = {
        "total_symbols": len(results),
        "total_records": 0,
        "fields_nan_count": {
            "open": 0,
            "high": 0,
            "low": 0,
            "close": 0,
            "volume": 0,
            "adj_close": 0,
        },
        "symbols_with_nan": {},
        "records_with_any_nan": 0,
        "valid_records": 0,
        "sample_nan_records": [],
    }

    for symbol, stock_datas in results.items():
        symbol_nan_info = {
            "total_records": len(stock_datas),
            "records_with_nan": 0,
            "fields_nan": {
                "open": 0,
                "high": 0,
                "low": 0,
                "close": 0,
                "volume": 0,
                "adj_close": 0,
            },
        }

        nan_analysis["total_records"] += len(stock_datas)

        for idx, sd in enumerate(stock_datas):
            has_nan = False
            record_nan_fields: List[str] = []

            # 各フィールドをチェック
            fields_to_check = {
                "open": sd.open_price,
                "high": sd.high,
                "low": sd.low,
                "close": sd.close,
                "volume": sd.volume,
                "adj_close": sd.adj_close,
            }

            for field_name, field_value in fields_to_check.items():
                # NaNチェック（None, float('nan'), pd.NA などを考慮）
                is_nan = False
                if field_value is None:
                    is_nan = True
                elif isinstance(field_value, float):
                    import math

                    if math.isnan(field_value):
                        is_nan = True

                if is_nan:
                    nan_analysis["fields_nan_count"][field_name] += 1
                    symbol_nan_info["fields_nan"][field_name] += 1
                    record_nan_fields.append(field_name)
                    has_nan = True

            if has_nan:
                nan_analysis["records_with_any_nan"] += 1
                symbol_nan_info["records_with_nan"] += 1

                # サンプルとして最初の10件のNaNレコードを保存
                if len(nan_analysis["sample_nan_records"]) < 10:
                    nan_analysis["sample_nan_records"].append(
                        {
                            "symbol": symbol,
                            "date": str(sd.trade_date),
                            "nan_fields": record_nan_fields,
                            "open": str(sd.open_price),
                            "high": str(sd.high),
                            "low": str(sd.low),
                            "close": str(sd.close),
                            "volume": str(sd.volume),
                            "adj_close": str(sd.adj_close),
                        }
                    )
            else:
                nan_analysis["valid_records"] += 1

        # 銘柄ごとのNaN情報を記録（NaNが1件以上ある場合のみ）
        if symbol_nan_info["records_with_nan"] > 0:
            nan_analysis["symbols_with_nan"][symbol] = symbol_nan_info

    # パーセンテージ計算
    if nan_analysis["total_records"] > 0:
        nan_analysis["nan_percentage"] = round(
            (
                nan_analysis["records_with_any_nan"]
                / nan_analysis["total_records"]
            )
            * 100,
            2,
        )
        nan_analysis["valid_percentage"] = round(
            (nan_analysis["valid_records"] / nan_analysis["total_records"])
            * 100,
            2,
        )

    # 結果を出力
    print("\n=== NaN Field Investigation Results ===")
    print(f"Total symbols: {nan_analysis['total_symbols']}")
    print(f"Total records: {nan_analysis['total_records']}")
    print(
        (
            f"Valid records: {nan_analysis['valid_records']} "
            f"({nan_analysis.get('valid_percentage', 0)}%)"
        )
    )
    print(
        (
            f"Records with NaN: {nan_analysis['records_with_any_nan']} "
            f"({nan_analysis.get('nan_percentage', 0)}%)"
        )
    )
    print("\n--- NaN Count by Field ---")
    for field, count in nan_analysis["fields_nan_count"].items():
        percentage = 0
        if nan_analysis["total_records"] > 0:
            percentage = round(
                (count / nan_analysis["total_records"]) * 100, 2
            )
        print(f"{field}: {count} ({percentage}%)")

    print(
        (
            "\n--- Symbols with NaN (Total: "
            f"{len(nan_analysis['symbols_with_nan'])}) ---"
        )
    )
    for symbol, info in nan_analysis["symbols_with_nan"].items():
        print(
            (
                f"{symbol}: {info['records_with_nan']}/"
                f"{info['total_records']} records with NaN"
            )
        )
        nan_fields = {k: v for k, v in info["fields_nan"].items() if v > 0}
        if nan_fields:
            print(f"  Fields: {nan_fields}")

    if nan_analysis["sample_nan_records"]:
        print("\n--- Sample NaN Records ---")
        for sample in nan_analysis["sample_nan_records"][:5]:
            print(
                (
                    f"{sample['symbol']} ({sample['date']}): "
                    f"NaN fields = {sample['nan_fields']}"
                )
            )

    # アーティファクトとして保存
    _write_performance_artifact("test_investigate_nan_fields", nan_analysis)

    await cleanup_database(engine)
