"""E2E tests for stock price batch flow."""

# flake8: noqa

import time

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.utils.database import get_database_url
from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_table,
    fetch_stock_master_for_artifact,
    run_async_safely,
    verify_stock_master_has_data,
    verify_stocks_1d_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


async def _fetch_table_rows_for_1d():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.stock_price import Stocks1d
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(Stocks1d))
            rows = result.scalars().all()
            cols = [c.name for c in Stocks1d.__table__.columns]
            out = []
            for r in rows:
                row = {}
                for c in cols:
                    v = getattr(r, c)
                    try:
                        if hasattr(v, "isoformat"):
                            v = v.isoformat()
                    except Exception:
                        pass
                    row[c] = v
                out.append(row)
            return out
    finally:
        await engine.dispose()


def test_setup_stock_master_for_batch(client):
    """Setup: バッチ用マスタデータの投入を確認.

    手順:
    1. stock_master をクリーンアップ
    2. /api/v1/stock-master/fetch/sample でサンプルマスタを投入
    3. DB に格納されたことを確認（存在確認のみ）

    Note:
    バッチテスト用に sample_size を 5 に削減してテスト時間を短縮します。
    """
    from app.models.market_data.stock_master import StockMaster

    # 事前クリーンアップ
    cleanup_table(StockMaster)

    # APIを呼び出してマスタを投入
    sample_url = "/api/v1/stock-master/fetch/sample?sample_size=5&batch_size=5"
    response = client.post(sample_url)

    # レスポンス確認（入口）
    assert response.status_code in (
        200,
        201,
        204,
    ), f"Unexpected status code: {response.status_code}"

    # DB確認（出口）
    assert verify_stock_master_has_data(), "StockMaster テーブルに行がない"


def test_stock_price_batch_triggers_api(client):
    """API: stock_price batch を実行してレスポンスを確認.

    前提: StockMaster に交えるデータがあること（test_setup_stock_master_for_batch で投入済み）

    手順:
    1. POST /api/v1/stock-price/batch でバッチAPIを呼び出し
    2. レスポンス確認（入口）
    3. レスポンス構造を確認
    """

    # 前提条件: StockMaster に交えるデータがあること
    assert (
        verify_stock_master_has_data()
    ), "Precondition failed: StockMaster にデータが見つかりません"

    # バッチAPIを呼び出し
    payload = {"timeframe": "1d", "batch_size": 5}
    response = client.post("/api/v1/stock-price/batch", json=payload)

    # レスポンス確認（入口）
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
    batch_result = response.json()
    assert isinstance(batch_result, dict), "Response should be a dictionary"


def test_stock_price_batch_saves_to_db(client):
    """DB: stock_price batch 後、DBに格納されたことを確認.

    前提: StockMaster に交えるデータがあること（test_setup_stock_master_for_batch で投入済み）

    手順:
    1. Stocks1d をクリーンアップ（事前状態を明確にする）
    2. POST /api/v1/stock-price/batch でバッチAPIを呼び出し
    3. レスポンス確認（入口）
    4. DB検証（出口） - 存在確認のみ
    5. artifact を出力（デバッグ支援）
    """
    from app.models.market_data.stock_price import Stocks1d

    # 前提条件: StockMaster に交えるデータがあること
    assert (
        verify_stock_master_has_data()
    ), "Precondition failed: StockMaster にデータが見つかりません"

    # 事前: Stocks1d をクリーンアップ
    cleanup_table(Stocks1d)

    # バッチAPIを呼び出し
    payload = {"timeframe": "1d", "batch_size": 5}
    response = client.post("/api/v1/stock-price/batch", json=payload)

    # レスポンス確認（入口）
    assert response.status_code == 200, f"Unexpected status code: {response.status_code}"

    # DB検証（出口） - 存在確認のみ
    assert verify_stocks_1d_has_data(), "Stocks1d テーブルにデータが格納されていない"

    # artifact を出力（必須）
    rows = run_async_safely(_fetch_table_rows_for_1d())
    assert rows, "No Stocks1d data to write artifact"
    name = "test_stock_price_batch_saves_to_db_stocks_1d_artifact"
    write_csv_artifact(rows, name=name)
    assert_artifact_written(name)
