"""Stock price fetch E2E tests."""

# flake8: noqa

import asyncio
import time
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.utils.database import get_database_url
from tests.e2e.utils import run_async_safely, write_csv_artifact


async def _cleanup_batch_executions():
    """
    batch_executions テーブルの全レコードを削除する。
    CASCADE により batch_execution_details も削除される。
    """
    engine = create_async_engine(get_database_url())
    try:
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM batch_executions"))
            print("DEBUG: Cleanup - Batch execution records deleted")
    finally:
        await engine.dispose()


async def _fetch_table_rows_for_1d():
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.stock_data import Stocks1d
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


def test_stock_price_fetch_flow(client):
    """E2E: 株価 fetch_and_save の統合シナリオ。

    手順:
    1. 銘柄マスタのサンプル投入（必要なら）
    2. /stock-master/symbols から銘柄を取得
    3. POST /stock-price/fetch を呼び出してデータを取得・保存
    4. GET /stock-price/{symbol}/{timeframe} で DB にレコードがあることを確認
    5. DELETE /stock-price/{timeframe}/all でクリーンアップ
    """

    # 事前クリーンアップ
    try:
        client.delete("/api/v1/stock-price/1d/all")
    except Exception:
        pass

    client.delete("/api/v1/stock-master/reset")
    run_async_safely(_cleanup_batch_executions())

    try:
        # 1) sample を投入して銘柄を確保
        sample_url = "/api/v1/stock-master/fetch/sample?sample_size=10&batch_size=10"
        r_sample = client.post(sample_url)
        assert r_sample.status_code in (200, 201, 204)

        # 2) symbols を取得
        r_symbols = client.get("/api/v1/stock-master/symbols")
        assert r_symbols.status_code == 200
        data = r_symbols.json()
        symbols: List[str] = data.get("symbols") if isinstance(data, dict) else data
        assert isinstance(symbols, list) and len(symbols) > 0

        # pick up to 3 symbols to limit external calls
        targets = symbols[:3]

        # 3) POST fetch (timeframe=1d を使用)
        payload = {"symbols": targets, "timeframe": "1d"}
        r_fetch = client.post("/api/v1/stock-price/fetch", json=payload)
        assert r_fetch.status_code == 200
        fetch_result = r_fetch.json()
        assert isinstance(fetch_result, dict) and "results" in fetch_result
        results = fetch_result["results"]
        assert isinstance(results, list) and len(results) == len(targets)

        # 4) GET で DB に格納されたことを確認（少し待ってから取得を試みる）
        timeframe = "1d"
        found_any = False
        for symbol in targets:
            # retry briefly because external fetch/save may take a moment
            for attempt in range(3):
                r_get = client.get(f"/api/v1/stock-price/{symbol}/{timeframe}?limit=5")
                if r_get.status_code == 200:
                    body = r_get.json()
                    count = body.get("count") if isinstance(body, dict) else 0
                    if isinstance(count, int) and count > 0:
                        found_any = True
                        break
                time.sleep(1)
        assert found_any, "DB に保存された株価データが見つかりませんでした"

        # artifact: 保存されたテーブルの内容をCSVに出力
        try:
            rows = run_async_safely(_fetch_table_rows_for_1d())
            if rows:
                name = "test_stock_price_fetch_flow_stocks_1d_artifact"
                write_csv_artifact(rows, name=name)
        except Exception as e:
            print(f"DEBUG: failed to write stock price artifact: {e}")

    finally:
        # クリーンアップ: 株価データ削除
        try:
            r_del = client.delete("/api/v1/stock-price/1d/all")
            if r_del.status_code == 200:
                print("DEBUG: Cleanup - Deleted stock price data for 1d")
        except Exception as e:
            print(f"DEBUG: Failed to cleanup stock price data: {e}")

        # クリーンアップ: stock_master リセット
        try:
            client.delete("/api/v1/stock-master/reset")
            print("DEBUG: Cleanup - Stock master reset")
        except Exception as e:
            print(f"DEBUG: Failed to reset stock master: {e}")

        # クリーンアップ: batch_executions 削除
        try:
            run_async_safely(_cleanup_batch_executions())
        except Exception as e:
            print(f"DEBUG: Failed to cleanup batch executions: {e}")
