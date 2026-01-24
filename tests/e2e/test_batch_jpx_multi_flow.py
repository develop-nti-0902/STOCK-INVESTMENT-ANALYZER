import asyncio
import time

from app.models.stock_data import (
    Stocks1d,
    Stocks1h,
    Stocks1m,
    Stocks5m,
    Stocks15m,
    Stocks30m,
)
from tests.e2e.utils import write_csv_artifact


async def _fetch_table_rows(model):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(model))
            rows = result.scalars().all()
            cols = [c.name for c in model.__table__.columns]
            out = []
            for r in rows:
                row = {}
                for c in cols:
                    v = getattr(r, c)
                    # datetime -> isoformat for CSV readability
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


def test_jpx_all_multi_flow(client):
    """簡易フロー:

    1. `/api/v1/stock-master/refresh/sample` を呼び出して銘柄を 5 件作成
    2. `/api/v1/stock-master/symbols` から 5 件を取得し先頭を選択
    3. `/api/v1/batch/stock-data/jpx-all/multi` を 各タイムフレーム で実行
    4. クリーンアップでリセット
    """
    # 前準備: リセット
    r0 = client.delete("/api/v1/stock-master/reset")
    assert r0.status_code in (200, 404)

    try:
        # 1) sample 作成（sample_size=5, batch_size=5）
        r_sample = client.post(
            "/api/v1/stock-master/refresh/sample?sample_size=5&batch_size=5"
        )
        assert r_sample.status_code in (200, 201, 204)

        # 少し待ってデータが永続化されるのを待つ
        time.sleep(1)

        # 2) symbols を取得して先頭を選択
        r_symbols = client.get("/api/v1/stock-master/symbols")
        assert r_symbols.status_code == 200
        data = r_symbols.json()
        if isinstance(data, dict):
            symbols = data.get("symbols") or []
        else:
            symbols = data

        assert isinstance(
            symbols, list
        ), "symbols はリストである必要があります"
        assert len(symbols) >= 5, "期待する件数の銘柄が作成されていません"

        # 3) jpx-all/multi を複数の timeframes で実行（list_batch_size=5）
        timeframes = ["1m", "5m", "15m", "30m", "1h", "1d"]
        model_map = {
            "1m": Stocks1m,
            "5m": Stocks5m,
            "15m": Stocks15m,
            "30m": Stocks30m,
            "1h": Stocks1h,
            "1d": Stocks1d,
        }
        for tf in timeframes:
            payload = {"timeframe": tf, "list_batch_size": 5}
            r_job = client.post(
                "/api/v1/batch/stock-data/jpx-all/multi", json=payload
            )
            assert (
                r_job.status_code == 201
            ), f"job create failed for timeframe {tf}"
            job = r_job.json()
            job_id = job.get("job_id")
            assert job_id, f"ジョブIDが返却されていません (timeframe={tf})"

            # 4) ジョブステータスをポーリング
            status_url = f"/api/v1/batch/status/{job_id}"
            final_status = None
            timeout = 30
            start = time.time()
            while time.time() - start < timeout:
                r_status = client.get(status_url)
                assert r_status.status_code == 200
                s = r_status.json()
                st = s.get("status")
                if st is not None and st.upper() in ("COMPLETED", "FAILED"):
                    final_status = st.upper()
                    break
                time.sleep(1)

            assert (
                final_status is not None
            ), f"ジョブがタイムアウトしました (timeframe={tf})"
            assert final_status in (
                "COMPLETED",
                "FAILED",
            ), f"予期しないステータス: {final_status}"
            # 次の timeframe に進む前に少し待つ
            time.sleep(0.5)

            # artifact: ジョブ完了後に timeframe 対応テーブルを SELECT して CSV 出力
            try:
                model = model_map.get(tf)
                if model is not None:
                    rows = asyncio.run(_fetch_table_rows(model))
                    # ファイル名例: test_batch_jpx_multi_flow_{table}_3.csv
                    table_name = getattr(model, "__tablename__", tf)
                    name = (
                        f"test_batch_jpx_multi_flow_"
                        f"test_jpx_all_multi_flow_{table_name}_3"
                    )
                    write_csv_artifact(rows, name=name)
            except Exception as e:
                print(f"DEBUG: artifact write failed for {tf}: {e}")

    finally:
        # クリーンアップ
        client.delete("/api/v1/stock-master/reset")


def test_jpx_run_sequence_flow(client):
    """簡易フロー:

    1. `/api/v1/stock-master/refresh/sample` を呼び出して銘柄を 5 件作成
    2. `/api/v1/batch/stock-data/jpx-all/multi/run_sequence` 実行
    3. ジョブステータスをポーリングして完了を確認
    4. クリーンアップでリセット
    """
    # 前準備: リセット
    r0 = client.delete("/api/v1/stock-master/reset")
    assert r0.status_code in (200, 404)

    try:
        # 1) sample 作成（sample_size=5, batch_size=5）
        r_sample = client.post(
            "/api/v1/stock-master/refresh/sample?sample_size=5&batch_size=5"
        )
        assert r_sample.status_code in (200, 201, 204)

        # 少し待ってデータが永続化されるのを待つ
        time.sleep(1)

        # 2) run_sequence を実行 (batch_size を指定)
        r_job = client.post(
            "/api/v1/batch/stock-data/jpx-all/multi/run_sequence",
            json={"batch_size": 5},
        )
        assert (
            r_job.status_code == 201
        ), f"job create failed: {r_job.status_code}"
        job = r_job.json()
        job_id = job.get("job_id")
        assert job_id, "ジョブIDが返却されていません"

        # 3) ジョブステータスをポーリング
        status_url = f"/api/v1/batch/status/{job_id}"
        final_status = None
        timeout = 60
        start = time.time()
        while time.time() - start < timeout:
            r_status = client.get(status_url)
            assert r_status.status_code == 200
            s = r_status.json()
            st = s.get("status")
            if st is not None and st.upper() in ("COMPLETED", "FAILED"):
                final_status = st.upper()
                break
            time.sleep(1)

        assert final_status is not None, "ジョブがタイムアウトしました"
        assert final_status in (
            "COMPLETED",
            "FAILED",
        ), f"予期しないステータス: {final_status}"

    finally:
        # クリーンアップ
        client.delete("/api/v1/stock-master/reset")
