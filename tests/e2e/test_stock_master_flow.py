import asyncio
import time

from tests.e2e.utils import fetch_stock_master_for_artifact, write_csv_artifact


def test_stock_master_flow(client):
    """統合フローで `/api/v1/stock-master` の主要エンドポイントを検証する。

    処理順:
    1. POST /api/v1/stock-master/fetch/sample
    2. POST /api/v1/stock-master/fetch
    3. GET  /api/v1/stock-master/symbols
    4. GET  /api/v1/stock-master/symbols/market/{market}
    5. DELETE /api/v1/stock-master/reset (クリーンアップ)
    """
    # 前準備: リセット
    r0 = client.delete("/api/v1/stock-master/reset")
    assert r0.status_code in (200, 404)

    try:
        # 1) fetch/sample (テスト用パラメータ指定: sample_size=50 を使用)
        sample_url = "/api/v1/stock-master/fetch/sample?" "sample_size=50&batch_size=50"
        r_sample = client.post(sample_url)
        assert r_sample.status_code in (200, 201, 204)
        # レスポンスに sample_size=50 が反映されていることを簡易検証
        if r_sample.status_code == 200:
            data_sample = r_sample.json()
            assert "(sample_size=50)" in data_sample.get(
                "message", ""
            ), "sample_size=50 がレスポンスに含まれていません"

        # artifact: refresh/sample後のstock_masterデータを取得
        try:
            stock_master_data_sample = asyncio.run(fetch_stock_master_for_artifact())
            base_name_sample = "test_stock_master_flow_test_stock_master_flow_stock_master_1"
            write_csv_artifact(stock_master_data_sample, name=base_name_sample)
        except Exception as e:
            print(f"DEBUG: Failed to write artifact after refresh/sample: {e}")
            import traceback

            traceback.print_exc()

        # 2) fetch
        r_refresh = client.post("/api/v1/stock-master/fetch")
        assert r_refresh.status_code == 200
        refresh_data = r_refresh.json()
        assert isinstance(refresh_data.get("updated_count"), int)

        # artifact: refresh後のstock_masterデータを取得
        try:
            stock_master_data = asyncio.run(fetch_stock_master_for_artifact())
            base_name = "test_stock_master_flow_test_stock_master_flow_stock_master_2"
            write_csv_artifact(stock_master_data, name=base_name)
        except Exception as e:
            print(f"DEBUG: Failed to write artifact after refresh: {e}")
            import traceback

            traceback.print_exc()

        # 3) symbols - エンドポイントは {"symbols": [...], "count": n} を返すため対応
        symbols = []
        for attempt in range(2):
            r_symbols = client.get("/api/v1/stock-master/symbols")
            assert r_symbols.status_code == 200
            data = r_symbols.json()
            if isinstance(data, dict):
                symbols = data.get("symbols") or []
            else:
                # 互換性: 万が一旧仕様で直接リストを返す場合に対応
                symbols = data

            if isinstance(symbols, list) and len(symbols) > 0:
                break

            # 空の場合はサンプル投入して再取得（テスト用）
            client.post(sample_url)
            time.sleep(1)

        assert isinstance(symbols, list), "symbols はリストである必要があります"
        assert (
            len(symbols) > 0
        ), "symbols が空です。refresh が正しくデータを作成しているか確認してください"

        # 3) symbols/market/{market} - 指示に従い各市場フィルタで取得できることを検証する。
        candidate_markets = [
            "ETF・ETN",
            "PRO Market",
            "REIT・ベンチャーファンド・カントリーファンド・インフラファンド",
            "グロース（外国株式）",
            "グロース（内国株式）",
            "スタンダード（外国株式）",
            "スタンダード（内国株式）",
            "プライム（外国株式）",
            "プライム（内国株式）",
            "出資証券",
        ]
        market_results = {}
        for m in candidate_markets:
            url = f"/api/v1/stock-master/symbols/market/{m}"
            r_market = client.get(url)
            assert (
                r_market.status_code == 200
            ), f"{m} のエンドポイントが失敗しました: {r_market.status_code}"
            items = r_market.json()
            if isinstance(items, dict):
                items = items.get("symbols") or []
            assert isinstance(items, list), f"{m} のレスポンスがリストではありません"
            assert len(items) > 0, f"市場 {m} のsymbolsが空です"
            market_results[m] = items

        # (sample は先頭で実行済みのためここでは再実行しない)

    finally:
        # 5) クリーンアップ
        client.delete("/api/v1/stock-master/reset")
