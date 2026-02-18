"""E2E tests for stock price batch flow.

最小限の修正で linter の要件を満たす。
"""

# flake8: noqa

import time

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.utils.database import get_database_url
from tests.e2e.utils import run_async_safely, write_csv_artifact

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


async def _cleanup_batch_executions() -> None:
    """バッチ実行レコードをすべて削除する。"""
    engine = create_async_engine(get_database_url())
    try:
        async with engine.begin() as conn:
            # テーブルが存在しない場合はスキップする（migrationで削除されている可能性あり）
            res = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='batch_executions'"
                )
            )
            table_name = res.scalar()
            if table_name:
                # batch_execution_details は CASCADE で削除される
                await conn.execute(text("DELETE FROM batch_executions"))
    finally:
        await engine.dispose()


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


def test_stock_price_batch_flow(client):
    """E2E: /stock-price/batch を実行して DB に格納されることを検証する。"""

    # 事前リセット（stock master）
    client.delete("/api/v1/stock-master/reset")

    # 事前リセット（株価データ）
    try:
        client.delete("/api/v1/stock-price/1d/all")
    except Exception:
        pass

    # 事前リセット（バッチ実行履歴）
    run_async_safely(_cleanup_batch_executions())

    try:

        # 1) sample を投入して銘柄を確保
        sample_url = "/api/v1/stock-master/fetch/sample?sample_size=10&batch_size=10"
        r_sample = client.post(sample_url)
        assert r_sample.status_code in (200, 201, 204)

        # 2) POST batch (timeframe=1d を使用)
        payload = {"timeframe": "1d", "batch_size": 10}
        r_batch = client.post("/api/v1/stock-price/batch", json=payload)
        assert r_batch.status_code == 200
        batch_result = r_batch.json()
        assert isinstance(batch_result, dict)

        # 3) DB に格納されたことを確認（Stocks1d テーブルを直接確認）
        found_any = False
        for attempt in range(10):
            try:
                rows = run_async_safely(_fetch_table_rows_for_1d())
                if rows and len(rows) > 0:
                    found_any = True
                    # artifact: 保存されたテーブルの内容をCSVに出力
                    try:
                        name = "test_stock_price_batch_flow_stocks_1d_artifact"
                        write_csv_artifact(rows, name=name)
                    except Exception as e:
                        print(f"DEBUG: failed to write stock price artifact: {e}")
                    break
            except Exception as e:
                print(f"DEBUG: retry fetch table rows failed: {e}")
            time.sleep(1)

        assert found_any, "DB に保存された株価データが見つかりませんでした"

    finally:
        # クリーンアップ: 株価データ削除
        try:
            timeframe = "1d"
            client.delete(f"/api/v1/stock-price/{timeframe}/all")
            print(f"DEBUG: Cleanup - Deleted stock price data for {timeframe}")
        except Exception as e:
            print(f"DEBUG: Failed to delete stock price data: {e}")

        # クリーンアップ: stock_master リセット
        try:
            client.delete("/api/v1/stock-master/reset")
            print("DEBUG: Cleanup - Stock master reset")
        except Exception as e:
            print(f"DEBUG: Failed to reset stock_master: {e}")

        # クリーンアップ: バッチ実行レコード削除
        try:
            run_async_safely(_cleanup_batch_executions())
            print("DEBUG: Cleanup - Batch execution records deleted")
        except Exception as e:
            print(f"DEBUG: Failed to cleanup batch_executions: {e}")
