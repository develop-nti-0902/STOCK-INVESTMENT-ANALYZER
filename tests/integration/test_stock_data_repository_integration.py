"""
株価データRepository統合テスト

実際のPostgreSQLデータベースを使用して、StockDataRepositoryの
UPSERT処理、データ取得、一括保存の動作を検証します。

実装: Issue #115 (統合テスト)
仕様書: docs/architecture/layers/data_access_layer.md
"""

import csv
import os
from datetime import datetime
from typing import List

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.models.stock_data import Stocks1d, Stocks1m
from app.repositories.stock_data_repository import (
    StockData1dRepository,
    StockData1mRepository,
)
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)


@pytest.fixture
def artifacts_dir():
    """統合テスト成果物の出力先ディレクトリ"""
    artifacts_path = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(artifacts_path, exist_ok=True)
    return artifacts_path


def export_to_csv(rows: List, fieldnames: List[str], filepath: str) -> None:
    """テスト結果をCSVにエクスポート"""
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row_data = {
                field: getattr(row, field, None) for field in fieldnames
            }
            writer.writerow(row_data)
    logger.info(f"Exported {len(rows)} records to {filepath}")


@pytest.mark.anyio
async def test_stock_data_1m_upsert_and_retrieve(monkeypatch, artifacts_dir):
    """
    1分足Repository: UPSERT処理とデータ取得の統合テスト

    検証内容:
    1. 新規データの挿入
    2. 同一データ（symbol + timestamp）の更新（UPSERT）
    3. 銘柄別データ取得
    4. 時間範囲指定での取得
    5. 最新データ取得
    """
    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:
        pytest.skip(f"DB接続設定が不足しています: {exc}")

    engine = create_async_engine(DATABASE_URL, echo=False)
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    # キャッシュクリア
    try:
        db_mod.get_session_maker.cache_clear()
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    session_maker = db_mod.get_session_maker()

    # テストデータ: トヨタ自動車（7203.T）1分足データ
    test_symbol = "7203.T"
    test_timestamp = datetime(2024, 1, 15, 9, 0, 0)

    # 前提条件: 銘柄マスタにテストデータを挿入
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.stock_master import StockMaster

    async with session_maker() as session:
        # 銘柄マスタデータの準備（既に存在する場合はスキップ）
        stmt = (
            pg_insert(StockMaster)
            .values(
                stock_code=test_symbol,
                stock_name="トヨタ自動車",
                market_category="Prime",
                sector_name_33="輸送用機器",
            )
            .on_conflict_do_nothing(index_elements=["stock_code"])
        )

        await session.execute(stmt)
        await session.commit()

    # フェーズ1: 新規データ挿入
    async with session_maker() as session:
        repo = StockData1mRepository(session)

        # 新規データ
        data_insert = {
            "symbol": test_symbol,
            "timestamp": test_timestamp,
            "open": 2500.0,
            "high": 2510.0,
            "low": 2495.0,
            "close": 2505.0,
            "volume": 10000,
        }

        result_insert = await repo.upsert_single(data_insert)
        await session.commit()
        logger.info(f"Insert result: {result_insert}")

        assert result_insert["operation"] == "upsert"
        assert result_insert["timeframe"] == "1m"
        assert result_insert["symbol"] == test_symbol

    # フェーズ2: 同一データの更新（UPSERT）
    async with session_maker() as session:
        repo = StockData1mRepository(session)

        # 価格データを更新
        data_update = {
            "symbol": test_symbol,
            "timestamp": test_timestamp,
            "open": 2500.0,
            "high": 2520.0,  # 変更
            "low": 2490.0,  # 変更
            "close": 2515.0,  # 変更
            "volume": 15000,  # 変更
        }

        result_update = await repo.upsert_single(data_update)
        await session.commit()
        logger.info(f"Update result: {result_update}")

        assert result_update["operation"] == "upsert"
        assert result_update["rowcount"] == 1

    # フェーズ3: データ取得検証
    async with session_maker() as session:
        repo = StockData1mRepository(session)

        # 銘柄コード + タイムスタンプでの取得
        retrieved = await repo.get_by_symbol_and_timestamp(
            test_symbol, test_timestamp
        )

        assert retrieved is not None
        assert retrieved.symbol == test_symbol
        assert retrieved.open == 2500.0
        assert retrieved.high == 2520.0  # 更新された値
        assert retrieved.low == 2490.0  # 更新された値
        assert retrieved.close == 2515.0  # 更新された値
        assert retrieved.volume == 15000  # 更新された値

        logger.info(f"Retrieved data: {retrieved}")

    # フェーズ4: 時間範囲取得
    async with session_maker() as session:
        repo = StockData1mRepository(session)

        start = datetime(2024, 1, 15, 8, 0, 0)
        end = datetime(2024, 1, 15, 10, 0, 0)
        range_data = await repo.get_by_symbol_and_range(
            test_symbol, start, end
        )

        assert len(range_data) >= 1
        assert all(r.symbol == test_symbol for r in range_data)
        logger.info(f"Range query returned {len(range_data)} records")

    # フェーズ5: 最新データ取得
    async with session_maker() as session:
        repo = StockData1mRepository(session)

        latest_data = await repo.get_latest(test_symbol, limit=5)

        assert len(latest_data) >= 1
        assert latest_data[0].symbol == test_symbol
        logger.info(f"Latest query returned {len(latest_data)} records")

    # 成果物出力
    async with session_maker() as session:
        result = await session.execute(
            select(Stocks1m).where(Stocks1m.symbol == test_symbol)
        )
        rows = result.scalars().all()

        if rows:
            # ファイル名に日時を含めず、再実行時は上書き保存する
            filename = "stock_data_1m_integration.csv"
            filepath = os.path.join(artifacts_dir, filename)

            fieldnames = [
                "id",
                "symbol",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "created_at",
                "updated_at",
            ]

            export_to_csv(rows, fieldnames, filepath)


@pytest.mark.anyio
async def test_stock_data_1d_bulk_upsert(monkeypatch, artifacts_dir):
    """
    日足Repository: 一括UPSERT処理の統合テスト

    検証内容:
    1. 複数レコードの一括挿入
    2. 一部重複データを含む一括UPSERT
    3. 挿入・更新件数の検証
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

    test_symbol = "9984.T"  # ソフトバンクグループ

    # 前提条件: 銘柄マスタにテストデータを挿入
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.stock_master import StockMaster

    async with session_maker() as session:
        stmt = (
            pg_insert(StockMaster)
            .values(
                stock_code=test_symbol,
                stock_name="ソフトバンクグループ",
                market_category="Prime",
                sector_name_33="情報・通信業",
            )
            .on_conflict_do_nothing(index_elements=["stock_code"])
        )

        await session.execute(stmt)
        await session.commit()

    # フェーズ1: 複数レコードの一括挿入
    async with session_maker() as session:
        repo = StockData1dRepository(session)

        # 3日分のデータ
        bulk_data = [
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 15, 0, 0, 0),
                "open": 5000.0,
                "high": 5100.0,
                "low": 4950.0,
                "close": 5050.0,
                "volume": 1000000,
            },
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 16, 0, 0, 0),
                "open": 5050.0,
                "high": 5150.0,
                "low": 5000.0,
                "close": 5100.0,
                "volume": 1200000,
            },
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 17, 0, 0, 0),
                "open": 5100.0,
                "high": 5200.0,
                "low": 5050.0,
                "close": 5150.0,
                "volume": 1100000,
            },
        ]

        result = await repo.upsert_bulk(bulk_data)
        await session.commit()
        logger.info(f"Bulk insert result: {result}")

        assert result == 3  # 3件成功

    # フェーズ2: 一部重複データを含む一括UPSERT
    async with session_maker() as session:
        repo = StockData1dRepository(session)

        # 2レコードは既存、1レコードは新規
        bulk_data_mixed = [
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 16, 0, 0, 0),  # 既存（更新）
                "open": 5050.0,
                "high": 5200.0,  # 変更
                "low": 5000.0,
                "close": 5180.0,  # 変更
                "volume": 1500000,  # 変更
            },
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 17, 0, 0, 0),  # 既存（更新）
                "open": 5100.0,
                "high": 5250.0,  # 変更
                "low": 5050.0,
                "close": 5200.0,  # 変更
                "volume": 1300000,  # 変更
            },
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 18, 0, 0, 0),  # 新規
                "open": 5200.0,
                "high": 5300.0,
                "low": 5150.0,
                "close": 5250.0,
                "volume": 1400000,
            },
        ]

        result = await repo.upsert_bulk(bulk_data_mixed)
        await session.commit()
        logger.info(f"Bulk upsert (mixed) result: {result}")

        assert result == 3  # 3件成功

    # データ検証
    async with session_maker() as session:
        repo = StockData1dRepository(session)

        # 1月16日のデータが更新されていることを確認
        data_1_16 = await repo.get_by_symbol_and_timestamp(
            test_symbol, datetime(2024, 1, 16, 0, 0, 0)
        )
        assert data_1_16 is not None
        assert data_1_16.high == 5200.0  # 更新された値
        assert data_1_16.close == 5180.0  # 更新された値

        # 1月18日の新規データが挿入されていることを確認
        data_1_18 = await repo.get_by_symbol_and_timestamp(
            test_symbol, datetime(2024, 1, 18, 0, 0, 0)
        )
        assert data_1_18 is not None
        assert data_1_18.close == 5250.0

    # 成果物出力
    async with session_maker() as session:
        result = await session.execute(
            select(Stocks1d).where(Stocks1d.symbol == test_symbol)
        )
        rows = result.scalars().all()

        if rows:
            # ファイル名に日時を含めず、再実行時は上書き保存する
            filename = "stock_data_1d_bulk_upsert.csv"
            filepath = os.path.join(artifacts_dir, filename)

            fieldnames = [
                "id",
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "adj_close",
                "volume",
                "created_at",
                "updated_at",
            ]

            export_to_csv(rows, fieldnames, filepath)


@pytest.mark.anyio
async def test_stock_data_count_and_latest(monkeypatch):
    """
    データ集計とソート取得の統合テスト

    検証内容:
    1. 銘柄別レコード数カウント
    2. 最新データ取得（降順ソート）
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

    test_symbol = "6758.T"  # ソニーグループ

    # 前提条件: 銘柄マスタにテストデータを挿入
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.models.stock_master import StockMaster

    async with session_maker() as session:
        stmt = (
            pg_insert(StockMaster)
            .values(
                stock_code=test_symbol,
                stock_name="ソニーグループ",
                market_category="Prime",
                sector_name_33="電気機器",
            )
            .on_conflict_do_nothing(index_elements=["stock_code"])
        )

        await session.execute(stmt)
        await session.commit()

    async with session_maker() as session:
        repo = StockData1dRepository(session)

        # テストデータの挿入
        test_data = [
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 10, 0, 0, 0),
                "open": 12000.0,
                "high": 12100.0,
                "low": 11950.0,
                "close": 12050.0,
                "volume": 500000,
            },
            {
                "symbol": test_symbol,
                "timestamp": datetime(2024, 1, 11, 0, 0, 0),
                "open": 12050.0,
                "high": 12150.0,
                "low": 12000.0,
                "close": 12100.0,
                "volume": 550000,
            },
        ]

        await repo.upsert_bulk(test_data)
        await session.commit()

        # レコード数カウント
        count = await repo.count_by_symbol(test_symbol)
        assert count >= 2
        logger.info(f"Record count for {test_symbol}: {count}")

        # 最新データ取得（降順）
        latest = await repo.get_latest(test_symbol, limit=2)
        assert len(latest) >= 1
        assert latest[0].timestamp >= latest[-1].timestamp  # 降順確認
        logger.info(
            f"Latest record: {latest[0].timestamp}, close: {latest[0].close}"
        )
