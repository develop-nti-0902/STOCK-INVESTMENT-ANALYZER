"""E2Eテスト: EDINET 日付範囲バッチ処理API.

このテストは実際のEDINET APIを呼び出すため、ネットワーク接続が必要です。
テスト実行時間を短縮するため、max_documentsを制限しています。
"""

from datetime import date

import pytest

from tests.e2e.utils import run_async_safely, write_csv_artifact, write_json_artifact


async def _fetch_edinet_balance_sheet_rows():
    """edinet_balance_sheets テーブルから全データを取得する.

    Returns:
        edinet_balance_sheets テーブルの全レコードを辞書のリストで返す
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetBalanceSheet
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


async def _fetch_edinet_profit_and_loss_rows():
    """edinet_profit_and_loss テーブルから全データを取得する.

    Returns:
        edinet_profit_and_loss テーブルの全レコードを辞書のリストで返す
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetProfitAndLoss
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(EdinetProfitAndLoss))
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "sec_code": row.sec_code,
                    "doc_id": row.doc_id,
                    "period_end_date": (
                        row.period_end_date.isoformat() if row.period_end_date else None
                    ),
                    "submission_date": (
                        row.submission_date.isoformat() if row.submission_date else None
                    ),
                    "fiscal_year": row.fiscal_year,
                    "report_type": row.report_type,
                    "net_sales": float(row.net_sales) if row.net_sales is not None else None,
                    "operating_income": (
                        float(row.operating_income) if row.operating_income is not None else None
                    ),
                    "eps": float(row.eps) if row.eps is not None else None,
                    "candidate_contexts": row.candidate_contexts,
                    "candidate_keys": row.candidate_keys,
                    "is_consolidated": row.is_consolidated,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]
    finally:
        await engine.dispose()


async def _fetch_edinet_stock_dividend_rows():
    """edinet_stock_dividend テーブルから全データを取得する.

    Returns:
        edinet_stock_dividend テーブルの全レコードを辞書のリストで返す
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetStockDividend
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(EdinetStockDividend))
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "sec_code": row.sec_code,
                    "doc_id": row.doc_id,
                    "period_end_date": (
                        row.period_end_date.isoformat() if row.period_end_date else None
                    ),
                    "submission_date": (
                        row.submission_date.isoformat() if row.submission_date else None
                    ),
                    "fiscal_year": row.fiscal_year,
                    "report_type": row.report_type,
                    "dividend_actual": (
                        float(row.dividend_actual) if row.dividend_actual is not None else None
                    ),
                    "candidate_contexts": row.candidate_contexts,
                    "candidate_keys": row.candidate_keys,
                    "is_consolidated": row.is_consolidated,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]
    finally:
        await engine.dispose()


async def _fetch_edinet_cash_flow_statement_rows():
    """edinet_cash_flow_statement テーブルから全データを取得する.

    Returns:
        edinet_cash_flow_statement テーブルの全レコードを辞書のリストで返す
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetCashFlowStatement
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            result = await session.execute(select(EdinetCashFlowStatement))
            rows = result.scalars().all()
            return [
                {
                    "id": row.id,
                    "sec_code": row.sec_code,
                    "doc_id": row.doc_id,
                    "period_end_date": (
                        row.period_end_date.isoformat() if row.period_end_date else None
                    ),
                    "submission_date": (
                        row.submission_date.isoformat() if row.submission_date else None
                    ),
                    "fiscal_year": row.fiscal_year,
                    "report_type": row.report_type,
                    "operating_cf": (
                        float(row.operating_cf) if row.operating_cf is not None else None
                    ),
                    "candidate_contexts": row.candidate_contexts,
                    "candidate_keys": row.candidate_keys,
                    "is_consolidated": row.is_consolidated,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
                for row in rows
            ]
    finally:
        await engine.dispose()


async def _cleanup_edinet_stock_dividend():
    """edinet_stock_dividend テーブルのデータをクリーンアップする."""
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetStockDividend
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            await session.execute(delete(EdinetStockDividend))
            await session.commit()
    finally:
        await engine.dispose()


async def _cleanup_edinet_cash_flow_statement():
    """edinet_cash_flow_statement テーブルのデータをクリーンアップする."""
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetCashFlowStatement
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            await session.execute(delete(EdinetCashFlowStatement))
            await session.commit()
    finally:
        await engine.dispose()


async def _cleanup_edinet_balance_sheets():
    """edinet_balance_sheets テーブルのデータをクリーンアップする."""
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetBalanceSheet
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            await session.execute(delete(EdinetBalanceSheet))
            await session.commit()
    finally:
        await engine.dispose()


async def _cleanup_edinet_profit_and_loss():
    """edinet_profit_and_loss テーブルのデータをクリーンアップする."""
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    from app.models.market_data.edinet import EdinetProfitAndLoss
    from app.utils.database import get_database_url

    engine = create_async_engine(get_database_url())
    try:
        async with AsyncSession(engine) as session:
            await session.execute(delete(EdinetProfitAndLoss))
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.slow
def test_edinet_process_date_range_flow(client):
    """E2E: EDINET 日付範囲バッチ処理を実行してDBに格納されることを検証する.

    手順:
    1. 事前クリーンアップ（edinet_balance_sheets と edinet_profit_and_loss テーブル）
    2. POST /api/v1/edinet/process-date-range を呼び出す
       - テスト用に max_documents=2 で制限
       - 2025-06-25の1日間を対象
    3. 処理結果を確認（同期実行）
    4. DB に貸借対照表と損益計算書のレコードが保存されたことを確認
    5. アーティファクトとして結果を保存
    6. クリーンアップ
    """
    # 1) 事前クリーンアップ
    try:
        run_async_safely(_cleanup_edinet_balance_sheets())
        run_async_safely(_cleanup_edinet_profit_and_loss())
        run_async_safely(_cleanup_edinet_stock_dividend())
        run_async_safely(_cleanup_edinet_cash_flow_statement())
    except Exception as e:
        print(f"DEBUG: cleanup before test failed (may be acceptable): {e}")

    # 2) EDINET 日付範囲バッチ実行（テスト用に制限）
    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 2,
        "progress_interval": 1,
        "transaction_atomic": True,
    }

    print(f"DEBUG: Requesting EDINET process-date-range with params: {params}")

    r_batch = client.post("/api/v1/edinet/process-date-range", params=params)

    # 処理が正常に完了するか、もしくはデータが見つからない場合も許容
    assert r_batch.status_code in (
        200,
        400,
        422,
    ), f"Unexpected status code: {r_batch.status_code}, response: {r_batch.text}"

    if r_batch.status_code != 200:
        print(
            f"DEBUG: EDINET returned non-200 status: {r_batch.status_code}, "
            f"response: {r_batch.text}"
        )
        pytest.skip("EDINET did not return 200, possibly no data available")
        return

    batch_result = r_batch.json()
    print(f"DEBUG: EDINET result: {batch_result}")

    # 3) 処理結果の確認（同期実行のため即座に完了）
    assert isinstance(batch_result, dict), "Response should be a dictionary"
    assert "status" in batch_result, "Response should contain status"
    assert "total_documents" in batch_result, "Response should contain total_documents"
    assert "processed_documents" in batch_result, "Response should contain processed_documents"
    assert "saved_items" in batch_result, "Response should contain saved_items"
    assert "failed_documents" in batch_result, "Response should contain failed_documents"

    # 結果のアーティファクト保存
    try:
        artifact_name = "test_edinet_process_date_range_result"
        write_json_artifact(batch_result, name=artifact_name)
    except Exception as e:
        print(f"DEBUG: Failed to write result artifact: {e}")

    # データが見つからない場合は早期リターン
    if batch_result.get("total_documents", 0) == 0:
        print("DEBUG: No documents found by EDINET API, skipping DB verification")
        pytest.skip("No documents found by EDINET API in the specified period")
        return

    # 4) DB にレコードが保存されたことを確認
    balance_sheet_rows = []
    profit_and_loss_rows = []
    cash_flow_rows = []

    try:
        balance_sheet_rows = run_async_safely(_fetch_edinet_balance_sheet_rows())
        print(f"DEBUG: Found {len(balance_sheet_rows)} balance sheet records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch balance sheet rows: {e}")

    try:
        profit_and_loss_rows = run_async_safely(_fetch_edinet_profit_and_loss_rows())
        print(f"DEBUG: Found {len(profit_and_loss_rows)} profit and loss records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch profit and loss rows: {e}")

    stock_dividend_rows = []
    try:
        stock_dividend_rows = run_async_safely(_fetch_edinet_stock_dividend_rows())
        print(f"DEBUG: Found {len(stock_dividend_rows)} stock dividend records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch stock dividend rows: {e}")

    try:
        cash_flow_rows = run_async_safely(_fetch_edinet_cash_flow_statement_rows())
        print(f"DEBUG: Found {len(cash_flow_rows)} cash flow records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch cash flow rows: {e}")

    # 少なくとも1つのテーブルにデータが格納されていることを確認
    assert (
        len(balance_sheet_rows) > 0
        or len(profit_and_loss_rows) > 0
        or len(stock_dividend_rows) > 0
        or len(cash_flow_rows) > 0
    ), f"DB に保存されたEDINETデータが見つかりませんでした。Result: {batch_result}"

    # 5) アーティファクトとして保存
    if balance_sheet_rows:
        try:
            artifact_name = "test_edinet_process_date_range_balance_sheet_db_data"
            write_csv_artifact(balance_sheet_rows, name=artifact_name)
        except Exception as e:
            print(f"DEBUG: Failed to write balance sheet artifact: {e}")

    if profit_and_loss_rows:
        try:
            artifact_name = "test_edinet_process_date_range_profit_and_loss_db_data"
            write_csv_artifact(profit_and_loss_rows, name=artifact_name)
        except Exception as e:
            print(f"DEBUG: Failed to write profit and loss artifact: {e}")

    if stock_dividend_rows:
        try:
            artifact_name = "test_edinet_process_date_range_stock_dividend_db_data"
            write_csv_artifact(stock_dividend_rows, name=artifact_name)
        except Exception as e:
            print(f"DEBUG: Failed to write stock dividend artifact: {e}")

    if cash_flow_rows:
        try:
            artifact_name = "test_edinet_process_date_range_cash_flow_db_data"
            write_csv_artifact(cash_flow_rows, name=artifact_name)
        except Exception as e:
            print(f"DEBUG: Failed to write cash flow artifact: {e}")

    # 6) クリーンアップ
    try:
        run_async_safely(_cleanup_edinet_balance_sheets())
        run_async_safely(_cleanup_edinet_profit_and_loss())
        run_async_safely(_cleanup_edinet_stock_dividend())
        run_async_safely(_cleanup_edinet_cash_flow_statement())
        print("DEBUG: EDINET tables cleanup completed")
    except Exception as e:
        print(f"DEBUG: EDINET tables cleanup failed: {e}")


@pytest.mark.slow
def test_edinet_process_date_range_validation(client):
    """E2E: EDINET 日付範囲バッチAPIのバリデーションを検証する.

    手順:
    1. 不正な日付形式でリクエスト → 422エラー
    2. max_documents に負の値を指定 → 422エラー
    3. クリーンアップ
    """
    # 1) 不正な日付形式
    params_invalid_date = {
        "start_date": "invalid-date",
        "end_date": "2025-06-25",
        "max_documents": 1,
    }
    r_invalid = client.post("/api/v1/edinet/process-date-range", params=params_invalid_date)
    assert r_invalid.status_code in (400, 422), (
        f"Should return 400 or 422 for invalid date format, "
        f"got {r_invalid.status_code}: {r_invalid.text}"
    )

    # 2) max_documents に負の値
    params_negative_max = {
        "start_date": "2025-06-25",
        "end_date": "2025-06-25",
        "max_documents": -1,
    }
    r_negative = client.post("/api/v1/edinet/process-date-range", params=params_negative_max)
    assert r_negative.status_code in (400, 422), (
        f"Should return 400 or 422 for negative max_documents, "
        f"got {r_negative.status_code}: {r_negative.text}"
    )

    # 3) クリーンアップ
    try:
        run_async_safely(_cleanup_edinet_balance_sheets())
        run_async_safely(_cleanup_edinet_profit_and_loss())
        run_async_safely(_cleanup_edinet_stock_dividend())
        run_async_safely(_cleanup_edinet_cash_flow_statement())
        print("DEBUG: EDINET tables cleanup completed")
    except Exception as e:
        print(f"DEBUG: EDINET tables cleanup failed: {e}")
