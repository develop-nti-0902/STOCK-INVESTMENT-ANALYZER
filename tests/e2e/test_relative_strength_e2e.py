"""レラティブストレングス E2E テスト."""

# flake8: noqa

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.market_data.relative_strength.relative_strength import RelativeStrength
from app.models.market_data.stock_price import Stocks1d
from tests.e2e.utils import (
    cleanup_table,
    get_test_engine,
    run_async_safely,
    verify_stock_master_has_data,
    verify_stocks_1d_has_data,
)

# 全 e2e テストを同一 xdist ワーカーで直列実行
pytestmark = pytest.mark.xdist_group("e2e")


@pytest.fixture(scope="session", autouse=True)
def setup_relative_strength_test_data():
    """RSテスト用データセットアップ（セッション単位で一度だけ実行）.

    処理内容:
    1. relative_strength テーブルをクリーンアップ
    2. stock_master にデータが存在しない場合 → fetch/sample API で投入
    3. stocks_1d にデータが存在しない場合 → stock-price/batch API で投入
    """
    # relative_strength テーブルをクリーンアップ
    cleanup_table(RelativeStrength)
    print("✅ Cleaned up relative_strength table")

    # stock_master にデータが存在しない場合のみ実 API で投入
    if not verify_stock_master_has_data():
        print("🔧 stock_master が空のため、fetch/sample API を呼び出します...")
        with TestClient(app) as c:
            resp = c.post(
                "/api/v1/stock-master/fetch/sample",
                params={"sample_size": 10},
            )
            print(f"✅ stock-master fetch/sample: status={resp.status_code}")
    else:
        print("✅ stock_master にデータが存在します（スキップ）")

    # stocks_1d にデータが存在しない場合のみ実 API で投入
    if not verify_stocks_1d_has_data():
        print("🔧 stocks_1d が空のため、stock-price/batch API を呼び出します...")
        with TestClient(app) as c:
            resp = c.post(
                "/api/v1/stock-price/batch",
                json={"timeframe": "1d", "batch_size": 50, "period": "300d"},
            )
            print(f"✅ stock-price/batch: status={resp.status_code}")
    else:
        print("✅ stocks_1d にデータが存在します（スキップ）")

    yield


def test_relative_strength_setup(client: TestClient) -> None:
    """前提確認: stock_master と stocks_1d にデータが存在すること.

    手順:
    1. StockMaster テーブルにレコードが存在することを確認
    2. Stocks1d テーブルにレコードが存在することを確認
    3. 各テーブルのレコード数を表示
    """
    assert verify_stock_master_has_data(), "StockMaster テーブルにデータが見つかりません"
    assert verify_stocks_1d_has_data(), "Stocks1d テーブルにデータが見つかりません"

    async def _check_counts() -> None:
        async with get_test_engine() as engine:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(func.count()).select_from(Stocks1d))
                stocks_1d_count = result.scalar_one()
                print(f"✅ Stocks1d: {stocks_1d_count} records")

                result2 = await session.execute(select(func.count()).select_from(RelativeStrength))
                rs_count = result2.scalar_one()
                print(f"✅ RelativeStrength (before calc): {rs_count} records")

    run_async_safely(_check_counts())


def test_relative_strength_calculate_date(client: TestClient) -> None:
    """指定日付 RS 計算 API テスト.

    手順:
    1. stocks_1d の最新 timestamp から計算基準日を取得
    2. POST /api/v1/relative-strength/calculate/date を呼び出す
    3. レスポンス status が "completed" | "partial_error" | "no_data" であることを確認
    4. rowcount が int であることを確認
    5. relative_strength テーブルのレコード数を確認
    """
    if not verify_stock_master_has_data() or not verify_stocks_1d_has_data():
        pytest.skip("テストデータが不足しています（setup が正常に完了しませんでした）")

    # stocks_1d の最新日付を取得
    async def _get_latest_date():
        async with get_test_engine() as engine:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(func.max(Stocks1d.timestamp)))
                max_ts = result.scalar_one_or_none()
                if max_ts is None:
                    return None
                if hasattr(max_ts, "date"):
                    return max_ts.date()
                return max_ts

    latest_date = run_async_safely(_get_latest_date())
    if latest_date is None:
        pytest.skip("Stocks1d にデータが存在しないため、スキップします")

    print(f"📅 計算基準日: {latest_date}")

    # API 呼び出し
    payload = {"target_date": latest_date.isoformat()}
    response = client.post("/api/v1/relative-strength/calculate/date", json=payload)

    # ステータスコード確認
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # レスポンスボディ確認
    body = response.json()
    assert "status" in body, "Response missing 'status' key"
    assert body["status"] in [
        "completed",
        "partial_error",
        "no_data",
    ], f"Unexpected status: {body['status']}"

    assert "rowcount" in body, "Response missing 'rowcount' key"
    assert isinstance(body["rowcount"], int), "rowcount must be int"
    assert body["rowcount"] >= 0, f"rowcount must be >= 0, got {body['rowcount']}"

    assert "skipped_count" in body, "Response missing 'skipped_count' key"
    assert "error_count" in body, "Response missing 'error_count' key"

    # relative_strength テーブルのレコード数確認
    async def _count_rs() -> int:
        async with get_test_engine() as engine:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(func.count()).select_from(RelativeStrength))
                return result.scalar_one()

    rs_count = run_async_safely(_count_rs())
    print(
        f"✅ calculate/date: status={body['status']}, rowcount={body['rowcount']}, "
        f"skipped={body['skipped_count']}, errors={body['error_count']}, "
        f"db_count={rs_count}"
    )

    # status が "completed" または "partial_error" の場合、DB にレコードが存在することを確認
    if body["status"] in ["completed", "partial_error"]:
        assert rs_count > 0, (
            f"relative_strength テーブルにレコードが存在しません "
            f"(status={body['status']}, rowcount={body['rowcount']})"
        )


def test_relative_strength_calculate_all(client: TestClient) -> None:
    """全期間 RS 計算 API テスト.

    手順:
    1. POST /api/v1/relative-strength/calculate/all を呼び出す
    2. レスポンス status が "completed" | "partial_error" | "no_data" であることを確認
    3. total_symbols, total_rowcount が int であることを確認
    4. relative_strength テーブルのレコード数を確認（calculate/date より多いはず）
    """
    if not verify_stock_master_has_data() or not verify_stocks_1d_has_data():
        pytest.skip("テストデータが不足しています（setup が正常に完了しませんでした）")

    # API 呼び出し（ボディなし）
    response = client.post("/api/v1/relative-strength/calculate/all")

    # ステータスコード確認
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # レスポンスボディ確認
    body = response.json()
    assert "status" in body, "Response missing 'status' key"
    assert body["status"] in [
        "completed",
        "partial_error",
        "no_data",
    ], f"Unexpected status: {body['status']}"

    assert "total_symbols" in body, "Response missing 'total_symbols' key"
    assert isinstance(body["total_symbols"], int), "total_symbols must be int"
    assert body["total_symbols"] >= 0, f"total_symbols must be >= 0, got {body['total_symbols']}"

    assert "total_rowcount" in body, "Response missing 'total_rowcount' key"
    assert isinstance(body["total_rowcount"], int), "total_rowcount must be int"
    assert body["total_rowcount"] >= 0, f"total_rowcount must be >= 0, got {body['total_rowcount']}"

    assert "error_count" in body, "Response missing 'error_count' key"

    # relative_strength テーブルのレコード数確認
    async def _count_rs() -> int:
        async with get_test_engine() as engine:
            async with AsyncSession(engine) as session:
                result = await session.execute(select(func.count()).select_from(RelativeStrength))
                return result.scalar_one()

    rs_count = run_async_safely(_count_rs())
    print(
        f"✅ calculate/all: status={body['status']}, "
        f"total_symbols={body['total_symbols']}, total_rowcount={body['total_rowcount']}, "
        f"errors={body['error_count']}, db_count={rs_count}"
    )

    # status が "completed" または "partial_error" の場合、DB にレコードが存在することを確認
    if body["status"] in ["completed", "partial_error"]:
        assert rs_count > 0, (
            f"relative_strength テーブルにレコードが存在しません "
            f"(status={body['status']}, total_rowcount={body['total_rowcount']})"
        )
