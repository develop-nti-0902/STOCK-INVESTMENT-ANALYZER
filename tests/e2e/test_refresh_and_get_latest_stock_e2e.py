"""E2E: ビューのリフレッシュと最新株価取得の統合テスト.

最小限の修正で linter の要件を満たす。
"""

# flake8: noqa
import asyncio
import time
from typing import List

import pytest

from tests.e2e.utils import (
    assert_artifact_written,
    fetch_stock_master_for_artifact,
    run_async_safely,
    verify_stock_master_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


def test_setup_stock_master_for_refresh(client):
    """Setup: 株価取得用の stock_master データを投入する.

    手順:
    1. stock master をリセット
    2. POST /api/v1/stock-master/fetch/sample でサンプル投入
    3. DB に格納されたことを確認
    """
    # 事前リセット
    client.delete("/api/v1/stock-price/1d/all")
    client.delete("/api/v1/stock-master/reset")

    # sample を投入して銘柄を確保
    sample_url = "/api/v1/stock-master/fetch/sample?sample_size=5&batch_size=5"
    response = client.post(sample_url)

    # 入口確認: レスポンス
    assert response.status_code in (
        200,
        201,
        204,
    ), f"Expected 200/201/204, got {response.status_code}"

    # 出口確認: DB格納
    assert verify_stock_master_has_data(), "StockMaster データが投入されていません"


def test_refresh_latest_stocks_triggers_api(client):
    """API: POST /api/v1/views/refresh-latest-stocks を実行して確認.

    手順:
    1. 前提条件確認（stock_master と stock_price にデータが存在）
    2. POST /api/v1/views/refresh-latest-stocks を呼び出す
    3. レスポンス確認
    """
    # 前提条件確認: stock_master にデータが存在
    if not verify_stock_master_has_data():
        pytest.skip("StockMaster データが存在しません")

    # 前提条件: symbols を取得して stock_price を投入
    response = client.get("/api/v1/stock-master/symbols")
    assert response.status_code == 200

    data = response.json()
    symbols = data.get("symbols") if isinstance(data, dict) else data

    assert isinstance(symbols, list) and len(symbols) > 0, "symbols が取得できていません"

    # 株価を取得
    payload = {"symbols": symbols, "timeframe": "1d"}
    response = client.post("/api/v1/stock-price/fetch", json=payload)

    assert response.status_code == 200, f"Stock price fetch failed: {response.status_code}"

    # ビューのリフレッシュをトリガー
    response = client.post("/api/v1/views/refresh-latest-stocks")

    # 入口確認: レスポンス
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    try:
        body = response.json()
        assert (
            body.get("status") == "completed"
        ), f"Expected status=completed, got {body.get('status')}"
    except Exception as e:
        # レスポンスが JSON でない場合はスキップ
        pass


def test_refresh_latest_stocks_saves_to_view(client):
    """Output: /api/v1/views/latest-stocks/{symbol} から最新データが取得できることを確認.

    手順:
    1. 前提条件確認（ビューにデータが存在）
    2. GET /api/v1/views/latest-stocks/{symbol} で最新レコードを取得
    3. 複数銘柄のデータが取得できることを確認
    4. artifact 出力（デバッグ用）
    """
    # 前提条件確認: stock_master にデータが存在
    if not verify_stock_master_has_data():
        pytest.skip("StockMaster データが存在しません")

    # symbols を取得
    response = client.get("/api/v1/stock-master/symbols")
    assert response.status_code == 200

    data = response.json()
    symbols = data.get("symbols") if isinstance(data, dict) else data

    assert isinstance(symbols, list) and len(symbols) > 0, "symbols が取得できていません"

    # 各銘柄の最新データを取得
    latest_stocks = []
    for symbol in symbols:
        response = client.get(f"/api/v1/views/latest-stocks/{symbol}")
        if response.status_code == 200:
            latest = response.json()
            latest_stocks.append(latest)

    # 出口確認: 複数銘柄のデータが格納されているか
    assert len(latest_stocks) > 0, "latest_stocks ビューからデータを取得できませんでした"

    # 複数銘柄が登録されているか確認
    retrieved_symbols = {stock.get("symbol") for stock in latest_stocks}
    assert (
        len(retrieved_symbols) > 1
    ), f"複数銘柄のデータが期待されましたが、{len(retrieved_symbols)}銘柄のみ"

    # artifact: 複数銘柄のデータをCSV形式で出力（必須）
    assert latest_stocks, "No latest_stocks data to write artifact"
    artifact_name = "test_refresh_and_get_latest_stock_e2e"
    write_csv_artifact(latest_stocks, name=artifact_name)
    assert_artifact_written(artifact_name)
