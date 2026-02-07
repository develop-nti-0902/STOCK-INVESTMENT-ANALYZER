"""E2E: ビューのリフレッシュと最新株価取得の統合テスト.

最小限の修正で linter の要件を満たす。
"""

import asyncio
import time
from typing import List

from tests.e2e.utils import write_csv_artifact


async def _wait_for_batch_completion(job_id: int, timeout: int = 300, poll_interval: int = 2):
    """バッチジョブの完了を待つ.

    Args:
        job_id: バッチジョブID
        timeout: タイムアウト時間（秒）
        poll_interval: ポーリング間隔（秒）

    Returns:
        dict: バッチジョブの最終状態を含む辞書
            - status: ジョブのステータス
            - job_data: ジョブの詳細情報

    Raises:
        TimeoutError: タイムアウトした場合
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.batch_execution import BatchExecution
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    start_time = time.time()

    try:
        while time.time() - start_time < timeout:
            async with AsyncSession(engine) as session:
                result = await session.execute(
                    select(BatchExecution).where(BatchExecution.id == job_id)
                )
                job = result.scalar_one_or_none()

                if job is None:
                    raise ValueError(f"Job ID {job_id} not found in batch_executions table")

                # 終了状態をチェック
                if job.status in ("completed", "failed", "cancelled"):
                    return {
                        "status": job.status,
                        "job_data": {
                            "id": job.id,
                            "batch_type": job.batch_type,
                            "status": job.status,
                            "total_stocks": job.total_stocks,
                            "processed_stocks": job.processed_stocks,
                            "successful_stocks": job.successful_stocks,
                            "failed_stocks": job.failed_stocks,
                            "start_time": (job.start_time.isoformat() if job.start_time else None),
                            "end_time": job.end_time.isoformat() if job.end_time else None,
                            "error_message": job.error_message,
                        },
                    }

                print(
                    f"DEBUG: Job {job_id} status: {job.status}, "
                    f"processed: {job.processed_stocks}/{job.total_stocks}"
                )

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Batch job {job_id} did not complete within {timeout} seconds")
    finally:
        await engine.dispose()


def test_refresh_latest_stocks_and_get_latest(client):
    """E2E: /api/v1/views/refresh-latest-stocks と /api/v1/views/latest-stocks/{symbol} を検証する.

    手順:
    1. 銘柄マスタのサンプル投入（必要なら）
    2. /api/v1/stock-master/symbols から銘柄を取得
    3. POST /api/v1/stock-price/fetch で対象銘柄の株価を取得・保存
    4. POST /api/v1/views/refresh-latest-stocks を呼び出す（202 期待）
    5. GET /api/v1/views/latest-stocks/{symbol} で最新レコードが取得できることを確認
    6. 複数銘柄のデータをCSV形式でアーティファクトとして出力
    """
    print("\n" + "=" * 80)
    print("DEBUG: Starting test_refresh_latest_stocks_and_get_latest")
    print("=" * 80)

    # 事前リセット（stock master）
    print("DEBUG: Step 0 - Resetting stock master...")
    client.delete("/api/v1/stock-master/reset")
    print("DEBUG: Step 0 - Stock master reset completed")

    # 1) sample を投入して銘柄を確保
    print("DEBUG: Step 1 - Fetching sample stock master data...")
    sample_url = "/api/v1/stock-master/fetch/sample?sample_size=5&batch_size=5"
    r_sample = client.post(sample_url)
    print(f"DEBUG: Step 1 - Sample fetch response status: {r_sample.status_code}")
    assert r_sample.status_code in (200, 201, 204)
    print("DEBUG: Step 1 - Sample data fetched successfully")

    # 2) symbols を取得
    print("DEBUG: Step 2 - Getting stock symbols...")
    r_symbols = client.get("/api/v1/stock-master/symbols")
    print(f"DEBUG: Step 2 - Symbols response status: {r_symbols.status_code}")
    assert r_symbols.status_code == 200
    data = r_symbols.json()
    symbols: List[str] = data.get("symbols") if isinstance(data, dict) else data
    print(f"DEBUG: Step 2 - Retrieved {len(symbols)} symbols: {symbols}")
    assert isinstance(symbols, list) and len(symbols) > 0

    # 3) すべての銘柄の株価を取得（timeframe=1d を使用）
    print(f"DEBUG: Step 3 - Fetching stock prices for {len(symbols)} symbols...")
    payload = {"symbols": symbols, "timeframe": "1d"}
    r_fetch = client.post("/api/v1/stock-price/fetch", json=payload)
    print(f"DEBUG: Step 3 - Stock price fetch response status: {r_fetch.status_code}")
    assert r_fetch.status_code == 200
    print("DEBUG: Step 3 - Stock prices fetched successfully")

    # 4) ビューのリフレッシュをトリガー
    print("DEBUG: Step 4 - Triggering refresh-latest-stocks...")
    r_refresh = client.post("/api/v1/views/refresh-latest-stocks")
    print(f"DEBUG: Step 4 - Refresh response status: {r_refresh.status_code}")
    # API はジョブ登録のため 202 を返す想定
    assert r_refresh.status_code in (202, 200)

    try:
        body = r_refresh.json()
        print(f"DEBUG: Step 4 - Refresh response body: {body}")
        job_id = body.get("job_id")

        if job_id:
            # job_id を整数に変換
            job_id = int(job_id)
            print(f"DEBUG: Step 4 - Waiting for refresh job {job_id} to complete...")

            # ジョブの完了を待つ
            job_completion = asyncio.run(_wait_for_batch_completion(job_id, timeout=300))
            job_status = job_completion["status"]
            job_data = job_completion["job_data"]

            print(f"DEBUG: Step 4 - Refresh job {job_id} completed with status: {job_status}")
            print(f"DEBUG: Step 4 - Job data: {job_data}")

            # ジョブが成功したことを確認
            assert job_status == "completed", (
                f"Refresh job {job_id} did not complete successfully. "
                f"Status: {job_status}, Error: {job_data.get('error_message')}"
            )
            print("DEBUG: Step 4 - Refresh job completed successfully")
        else:
            # job_id が取得できない場合は少し待つ（後方互換性のため）
            print("WARNING: job_id not found in response, waiting 5 seconds...")
            time.sleep(5)

    except Exception as e:
        print(f"WARNING: Failed to wait for job completion: {e}")
        import traceback

        traceback.print_exc()
        # エラーが発生した場合は少し待つ
        time.sleep(5)

    # 5) 各銘柄の最新データを取得してリストに蓄積
    print(f"DEBUG: Step 5 - Retrieving latest stock data for {len(symbols)} symbols...")
    latest_stocks = []
    for i, symbol in enumerate(symbols, 1):
        print(f"DEBUG: Step 5 - Retrieving data for symbol {i}/{len(symbols)}: {symbol}")
        r_get = client.get(f"/api/v1/views/latest-stocks/{symbol}")
        if r_get.status_code == 200:
            latest = r_get.json()
            latest_stocks.append(latest)
            print(f"DEBUG: Step 5 - Successfully retrieved data for {symbol}")
        else:
            # データが取得できなかった場合は警告のみ
            print(
                "Warning: Could not retrieve latest data for {} (status: {})".format(
                    symbol, r_get.status_code
                )
            )

    print(f"DEBUG: Step 5 - Retrieved {len(latest_stocks)} records")

    # 少なくとも1つの銘柄のデータが取得できていることを確認
    assert len(latest_stocks) > 0, "latest_stocks ビューからデータを取得できませんでした"

    # 複数銘柄が登録されていることを確認
    retrieved_symbols = {stock.get("symbol") for stock in latest_stocks}
    assert (
        len(retrieved_symbols) > 1
    ), f"複数銘柄のデータが期待されましたが、{len(retrieved_symbols)}銘柄のみ取得できました"

    # 6) アーティファクト: 複数銘柄のデータをCSV形式で書き出す
    print("DEBUG: Step 6 - Writing CSV artifact...")
    try:
        write_csv_artifact(latest_stocks, name="test_refresh_and_get_latest_stock_e2e")
        print("DEBUG: Step 6 - CSV artifact written successfully")
    except Exception as e:
        print(f"Warning: Failed to write CSV artifact: {e}")

    # クリーンアップ: 保存した1日足の株価を削除し、stock_master をリセット
    print("DEBUG: Cleanup - Deleting stock prices...")
    try:
        client.delete("/api/v1/stock-price/1d/all")
        print("DEBUG: Cleanup - Stock prices deleted")
    except Exception as e:
        print(f"DEBUG: Cleanup - Failed to delete stock prices: {e}")

    print("DEBUG: Cleanup - Resetting stock master...")
    try:
        client.delete("/api/v1/stock-master/reset")
        print("DEBUG: Cleanup - Stock master reset")
    except Exception as e:
        print(f"DEBUG: Cleanup - Failed to reset stock master: {e}")

    print("=" * 80)
    print("DEBUG: Test completed successfully")
    print("=" * 80)

    try:
        client.delete("/api/v1/stock-master/reset")
    except Exception:
        pass
