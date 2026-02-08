"""E2Eテスト: EDINET 貸借対照表取得バッチAPI.

このテストは実際のEDINET APIを呼び出すため、ネットワーク接続が必要です。
テスト実行時間を短縮するため、max_documentsを制限しています。
"""

# flake8: noqa

import time
from datetime import date

import pytest

from tests.e2e.utils import run_async_safely, write_csv_artifact, write_json_artifact


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
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.batch_execution import BatchExecution
    from app.models.enums import BatchExecutionStatus
    from app.utils.database import get_database_url

    start_time = time.time()

    while time.time() - start_time < timeout:
        # 各イテレーションで新しいエンジンとセッションを作成
        # これにより、イベントループの問題を回避する
        engine = create_async_engine(get_database_url())
        try:
            async with AsyncSession(engine) as session:
                result = await session.execute(
                    select(BatchExecution).where(BatchExecution.id == job_id)
                )
                job = result.scalar_one_or_none()

                if job is None:
                    raise ValueError(f"Job ID {job_id} not found in batch_executions table")

                # 終了状態をチェック
                if job.status in (
                    BatchExecutionStatus.COMPLETED,
                    BatchExecutionStatus.FAILED,
                    BatchExecutionStatus.CANCELLED,
                ):
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
        finally:
            await engine.dispose()

        await asyncio.sleep(poll_interval)

    raise TimeoutError(f"Batch job {job_id} did not complete within {timeout} seconds")


async def _fetch_edinet_balance_sheet_rows():
    """edinet_balance_sheets テーブルから全データを取得する.

    Returns:
        edinet_balance_sheets テーブルの全レコードを辞書のリストで返す
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.edinet_balance_sheet import EdinetBalanceSheet
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(EdinetBalanceSheet))
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "sec_code": row.sec_code,
                    "filer_name": row.filer_name,
                    "doc_id": row.doc_id,
                    "period_end_date": (
                        row.period_end_date.isoformat() if row.period_end_date else None
                    ),
                    "submission_date": (
                        row.submission_date.isoformat() if row.submission_date else None
                    ),
                    "fiscal_year": row.fiscal_year,
                    "total_assets": float(row.total_assets) if row.total_assets else None,
                    "total_liabilities": (
                        float(row.total_liabilities) if row.total_liabilities else None
                    ),
                    "total_equity": float(row.total_equity) if row.total_equity else None,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]
    finally:
        await engine.dispose()


async def _cleanup_edinet_balance_sheets():
    """edinet_balance_sheets テーブルのデータをクリーンアップする."""
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.edinet_balance_sheet import EdinetBalanceSheet
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            await session.execute(delete(EdinetBalanceSheet))
            await session.commit()
    finally:
        await engine.dispose()


async def _cleanup_batch_executions(job_id: int):
    """バッチ実行レコードをクリーンアップする.

    Args:
        job_id: クリーンアップするバッチジョブID
    """
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.batch_execution import BatchExecution
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            # batch_execution_details テーブルは外部キー制約で自動削除される想定
            # または明示的に削除が必要な場合はここに追加
            await session.execute(delete(BatchExecution).where(BatchExecution.id == job_id))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.slow
def test_edinet_balance_sheet_batch_flow(client):
    """E2E: EDINET 貸借対照表取得バッチを実行してDBに格納されることを検証する.

    手順:
    1. 事前クリーンアップ（edinet_balance_sheets テーブル）
    2. POST /api/v1/edinet/balance-sheet を呼び出す
       - テスト用に max_documents=2 で制限
       - 直近1週間のデータを対象
    3. バッチ実行結果を確認
    4. DB にレコードが保存されたことを確認
    5. アーティファクトとして結果を保存
    6. クリーンアップ（edinet_balance_sheets と batch_executions）
    """
    from app.models.enums import BatchExecutionStatus

    job_id = None  # クリーンアップ用に job_id を保持

    # 1) 事前クリーンアップ
    try:
        run_async_safely(_cleanup_edinet_balance_sheets())
    except Exception as e:
        print(f"DEBUG: cleanup before test failed (may be acceptable): {e}")

    # 2) EDINET バッチ実行（テスト用に制限）
    # 2025-06-25を対象日としてデータを取得（max_documents=2で制限）
    target_date = date(2025, 6, 25)
    start_date = target_date
    end_date = target_date

    payload = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "progress_interval": 1,
        "max_documents": 2,
    }

    print(f"DEBUG: Requesting EDINET batch with payload: {payload}")

    r_batch = client.post("/api/v1/edinet/balance-sheet", json=payload)

    # バッチAPIが正常に完了するか、もしくはデータが見つからない場合も許容
    assert r_batch.status_code in (
        200,
        400,
        422,
    ), f"Unexpected status code: {r_batch.status_code}, response: {r_batch.text}"

    if r_batch.status_code != 200:
        print(
            f"DEBUG: EDINET batch returned non-200 status: {r_batch.status_code}, "
            f"response: {r_batch.text}"
        )
        # データが見つからない場合などは早期リターン
        pytest.skip("EDINET batch did not return 200, possibly no data available")
        return

    batch_result = r_batch.json()
    print(f"DEBUG: EDINET batch result: {batch_result}")

    # 3) バッチ実行結果の確認
    assert isinstance(batch_result, dict), "Response should be a dictionary"
    assert "job_id" in batch_result, "Response should contain job_id"
    assert "status" in batch_result, "Response should contain status"
    assert "total_documents" in batch_result, "Response should contain total_documents"
    assert "processed_documents" in batch_result, "Response should contain processed_documents"
    assert "saved_years" in batch_result, "Response should contain saved_years"
    assert "failed_documents" in batch_result, "Response should contain failed_documents"

    # 結果のアーティファクト保存
    try:
        artifact_name = "test_edinet_balance_sheet_batch_result"
        write_json_artifact(batch_result, name=artifact_name)
    except Exception as e:
        print(f"DEBUG: Failed to write batch result artifact: {e}")

    # 3.1) バッチジョブの完了を待つ
    job_id = int(batch_result["job_id"])  # 文字列の場合は整数に変換
    print(f"DEBUG: Waiting for batch job {job_id} to complete...")

    try:
        try:
            job_completion = run_async_safely(_wait_for_batch_completion(job_id, timeout=300))
            job_status = job_completion["status"]
            job_data = job_completion["job_data"]

            print(f"DEBUG: Batch job {job_id} completed with status: {job_status}")
            print(f"DEBUG: Job data: {job_data}")

            # ジョブが成功したことを確認
            assert job_status == BatchExecutionStatus.COMPLETED, (
                f"Batch job {job_id} did not complete successfully. "
                f"Status: {job_status}, Error: {job_data.get('error_message')}"
            )

            # ジョブデータのアーティファクト保存
            try:
                artifact_name = "test_edinet_balance_sheet_job_completion"
                write_json_artifact(job_data, name=artifact_name)
            except Exception as e:
                print(f"DEBUG: Failed to write job completion artifact: {e}")

        except TimeoutError as e:
            pytest.fail(f"Batch job {job_id} did not complete within timeout: {e}")
        except Exception as e:
            pytest.fail(f"Failed to wait for batch job completion: {e}")

        # 4) DB にレコードが保存されたことを確認
        found_any = False
        rows = []

        try:
            rows = run_async_safely(_fetch_edinet_balance_sheet_rows())
            if rows and len(rows) > 0:
                found_any = True
                print(f"DEBUG: Found {len(rows)} records in edinet_balance_sheets table")
        except Exception as e:
            print(f"DEBUG: Failed to fetch table rows: {e}")

        # データが見つからない場合でも、total_documents=0なら許容する
        if not found_any and batch_result.get("total_documents", 0) == 0:
            print("DEBUG: No documents found by EDINET API, skipping DB verification")
            pytest.skip("No documents found by EDINET API in the specified period")
            return

        # データがあるはずなのに見つからない場合はアサート失敗
        assert found_any, (
            f"DB に保存されたEDINET貸借対照表データが見つかりませんでした。"
            f"Batch result: {batch_result}"
        )

        # 5) アーティファクトとして保存
        try:
            artifact_name = "test_edinet_balance_sheet_batch_db_data"
            write_csv_artifact(rows, name=artifact_name)
        except Exception as e:
            print(f"DEBUG: Failed to write DB data artifact: {e}")

    finally:
        # 6) クリーンアップ（edinet_balance_sheets と batch_executions）
        try:
            run_async_safely(_cleanup_edinet_balance_sheets())
            print("DEBUG: edinet_balance_sheets cleanup completed")
        except Exception as e:
            print(f"DEBUG: edinet_balance_sheets cleanup failed: {e}")

        # バッチ実行レコードのクリーンアップ
        if job_id is not None:
            try:
                run_async_safely(_cleanup_batch_executions(job_id))
                print(f"DEBUG: batch_executions cleanup completed for job_id={job_id}")
            except Exception as e:
                print(f"DEBUG: batch_executions cleanup failed for job_id={job_id}: {e}")


@pytest.mark.slow
def test_edinet_balance_sheet_batch_validation(client):
    """E2E: EDINET バッチAPIのバリデーションを検証する.

    手順:
    1. 不正な日付形式でリクエスト → 400/422エラー
    2. end_date < start_date でリクエスト → 正常に処理されるか確認
    3. クリーンアップ（edinet_balance_sheets と batch_executions）
    """
    job_ids = []  # クリーンアップ用に job_id を収集

    try:
        # 1) 不正な日付形式
        invalid_payload = {
            "start_date": "invalid-date",
            "end_date": "2024-01-01",
            "max_documents": 1,
        }

        r_invalid = client.post("/api/v1/edinet/balance-sheet", json=invalid_payload)
        assert r_invalid.status_code in (
            400,
            422,
        ), f"Expected validation error, got: {r_invalid.status_code}"

        print("DEBUG: Validation test passed - invalid date format rejected")

        # 2) 日付範囲チェック（end_date < start_date）
        reversed_payload = {
            "start_date": "2024-01-10",
            "end_date": "2024-01-01",
            "max_documents": 1,
        }

        r_reversed = client.post("/api/v1/edinet/balance-sheet", json=reversed_payload)
        # 日付が逆転している場合、バッチは正常に完了するがデータが0件の可能性が高い
        # ただし、実装によってエラーになる場合もある
        assert r_reversed.status_code in (
            200,
            400,
            422,
        ), f"Expected success or validation error, got: {r_reversed.status_code}"

        # バッチが実行された場合、job_id を収集
        if r_reversed.status_code == 200:
            try:
                reversed_result = r_reversed.json()
                if "job_id" in reversed_result:
                    job_ids.append(int(reversed_result["job_id"]))
            except Exception as e:
                print(f"DEBUG: Failed to extract job_id from reversed payload: {e}")

        print(
            "DEBUG: Validation test passed - reversed date range handled: "
            f"{r_reversed.status_code}"
        )

    finally:
        # 3) クリーンアップ（edinet_balance_sheets と batch_executions）
        try:
            run_async_safely(_cleanup_edinet_balance_sheets())
            print("DEBUG: Validation test - edinet_balance_sheets cleanup completed")
        except Exception as e:
            print(f"DEBUG: Validation test - edinet_balance_sheets cleanup failed: {e}")

        # バッチ実行レコードのクリーンアップ
        for job_id in job_ids:
            try:
                run_async_safely(_cleanup_batch_executions(job_id))
                print(
                    f"DEBUG: Validation test - batch_executions cleanup completed for job_id={job_id}"
                )
            except Exception as e:
                print(
                    f"DEBUG: Validation test - batch_executions cleanup failed for job_id={job_id}: {e}"
                )
