import time

from tests.e2e.utils import write_csv_artifact


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


def test_stock_price_batch_flow(client):
    """E2E: /stock-price/batch を実行して DB に格納されることを検証する。

    手順:
    1. 銘柄マスタのサンプル投入（sample 10件）
    2. /stock-master/symbols から銘柄を取得
    3. POST /stock-price/batch を呼び出す（timeframe=1d, batch_size=10）
    4. GET /stock-price/{symbol}/{timeframe} で DB にレコードがあることを確認
    5. DELETE /stock-price/{timeframe}/all でクリーンアップ
    """

    # 事前リセット（stock master）
    client.delete("/api/v1/stock-master/reset")

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
            rows = __import__("asyncio").run(_fetch_table_rows_for_1d())
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

    # 4) cleanup: delete all for timeframe
    timeframe = "1d"
    r_del = client.delete(f"/api/v1/stock-price/{timeframe}/all")
    assert r_del.status_code == 200
