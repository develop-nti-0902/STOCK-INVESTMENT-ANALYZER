import time


def test_stock_master_flow(client):
    """統合フローで `/api/v1/stock-master` の主要エンドポイントを検証する。

    処理順:
    1. POST /api/v1/stock-master/refresh
    2. GET  /api/v1/stock-master/symbols
    3. GET  /api/v1/stock-master/symbols/market/{market}
    4. POST /api/v1/stock-master/refresh/sample
    5. DELETE /api/v1/stock-master/reset (クリーンアップ)
    """
    # 前準備: リセット
    r0 = client.delete("/api/v1/stock-master/reset")
    assert r0.status_code in (200, 404)

    try:
        # 1) refresh
        r_refresh = client.post("/api/v1/stock-master/refresh")
        assert r_refresh.status_code == 200
        refresh_data = r_refresh.json()
        assert isinstance(refresh_data.get("updated_count"), int)

        # 2) symbols - エンドポイントは {"symbols": [...], "count": n} を返すため対応
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

            # 空の場合はサンプル投入して再取得（テスト用: sample_size=50, batch_size=50）
            sample_url = (
                "/api/v1/stock-master/refresh/sample?"
                "sample_size=50&batch_size=50"
            )
            client.post(sample_url)
            time.sleep(1)

        assert isinstance(
            symbols, list
        ), "symbols はリストである必要があります"
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
            assert isinstance(
                items, list
            ), f"{m} のレスポンスがリストではありません"
            assert len(items) > 0, f"市場 {m} のsymbolsが空です"
            market_results[m] = items

        # 4) refresh/sample (テスト用パラメータ指定)
        r_sample = client.post(sample_url)
        assert r_sample.status_code in (200, 201, 204)

    finally:
        # 5) クリーンアップ
        client.delete("/api/v1/stock-master/reset")
