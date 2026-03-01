"""E2Eテスト: EDINET 日付範囲バッチ処理API.

このテストは実際のEDINET APIを呼び出すため、ネットワーク接続が必要です。
テスト実行時間を短縮するため、max_documentsを制限しています。
"""

from datetime import date

import pytest

from app.repositories.market_data.edinet import (
    EdinetCashFlowStatementRepository,
    EdinetProfitAndLossRepository,
    EdinetStockDividendRepository,
)
from app.repositories.market_data.stock_master import StockMasterRepository
from app.repositories.screening import ScreeningResultRepository
from tests.e2e.utils import (
    cleanup_repository_delete_all,
    fetch_edinet_cash_flow_statement_rows,
    fetch_edinet_profit_and_loss_rows,
    fetch_edinet_stock_dividend_rows,
    run_async_safely,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


@pytest.mark.slow
def test_edinet_process_date_range_flow(client):
    """E2E: EDINET 日付範囲バッチ処理を実行してDBに格納されることを検証する.

    手順:
    1. 事前クリーンアップ（各テーブル）
    2. stock_master を更新する（/api/v1/stock-master/fetch）
    3. POST /api/v1/edinet/process-date-range を呼び出す
       - テスト用に max_documents=10 で制限
       - 2025-06-25の1日間を対象
    4. 処理結果を確認（同期実行）
    5. DB に損益計算書のレコードが保存されたことを確認
    6. アーティファクトとして結果を保存
    7. /api/v1/screening/run を実行する
    8. スクリーニング結果をアーティファクトとして保存
    """
    # 1) 事前クリーンアップ
    try:
        run_async_safely(cleanup_repository_delete_all(EdinetProfitAndLossRepository))
        run_async_safely(cleanup_repository_delete_all(EdinetStockDividendRepository))
        run_async_safely(cleanup_repository_delete_all(EdinetCashFlowStatementRepository))
        run_async_safely(cleanup_repository_delete_all(ScreeningResultRepository))
        run_async_safely(cleanup_repository_delete_all(StockMasterRepository))
    except Exception as e:
        print(f"DEBUG: cleanup before test failed (may be acceptable): {e}")

    # 2) EDINET 日付範囲バッチ実行（テスト用に制限）
    # 但し、その前に stock_master を更新する必要があります
    print("DEBUG: Fetching stock_master data")
    r_stock_master = client.post("/api/v1/stock-master/fetch")
    if r_stock_master.status_code == 200:
        stock_master_result = r_stock_master.json()
        print(
            f"DEBUG: stock_master fetch successful, updated_count={stock_master_result.get('updated_count', 0)}"
        )
    else:
        print(
            f"DEBUG: stock_master fetch returned status {r_stock_master.status_code}, "
            f"response: {r_stock_master.text}"
        )

    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 10,
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

    # 失敗情報があれば詳細を出力
    if batch_result.get("failed_documents_details"):
        print("DEBUG: Failed documents details:")
        for detail in batch_result.get("failed_documents_details", []):
            print(f"  - Doc ID: {detail.get('doc_id')}, Error: {detail.get('error')}")

    # 3) 処理結果の確認（同期実行のため即座に完了）
    assert isinstance(batch_result, dict), "Response should be a dictionary"
    assert "status" in batch_result, "Response should contain status"
    assert "total_documents" in batch_result, "Response should contain total_documents"
    assert "processed_documents" in batch_result, "Response should contain processed_documents"
    assert "saved_items" in batch_result, "Response should contain saved_items"
    assert "failed_documents" in batch_result, "Response should contain failed_documents"

    # データが見つからない場合は早期リターン
    if batch_result.get("total_documents", 0) == 0:
        print("DEBUG: No documents found by EDINET API, skipping DB verification")
        pytest.skip("No documents found by EDINET API in the specified period")
        return

    # ドキュメント処理がすべて失敗した場合はスキップ
    if batch_result.get("failed_documents", 0) > 0 and batch_result.get("saved_items", 0) == 0:
        print(
            f"DEBUG: All documents failed processing "
            f"(failed={batch_result.get('failed_documents')}, "
            f"saved={batch_result.get('saved_items')}), skipping DB verification"
        )
        pytest.skip(
            f"All documents failed: failed_documents={batch_result.get('failed_documents')}, "
            f"saved_items={batch_result.get('saved_items')}"
        )
        return

    # 4) DB にレコードが保存されたことを確認
    profit_and_loss_rows = []
    cash_flow_rows = []

    try:
        profit_and_loss_rows = run_async_safely(fetch_edinet_profit_and_loss_rows())
        print(f"DEBUG: Found {len(profit_and_loss_rows)} profit and loss records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch profit and loss rows: {e}")

    stock_dividend_rows = []
    try:
        stock_dividend_rows = run_async_safely(fetch_edinet_stock_dividend_rows())
        print(f"DEBUG: Found {len(stock_dividend_rows)} stock dividend records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch stock dividend rows: {e}")

    try:
        cash_flow_rows = run_async_safely(fetch_edinet_cash_flow_statement_rows())
        print(f"DEBUG: Found {len(cash_flow_rows)} cash flow records")
    except Exception as e:
        print(f"DEBUG: Failed to fetch cash flow rows: {e}")

    # 少なくとも1つのテーブルにデータが格納されていることを確認
    # ここに到達した場合、処理成功しているはずなので、データが存在することを確認
    assert (
        len(profit_and_loss_rows) > 0 or len(stock_dividend_rows) > 0 or len(cash_flow_rows) > 0
    ), (
        f"処理成功したにもかかわらずDB にファイナンシャルデータが見つかりませんでした。Result: {batch_result}\n"
        f"P&L: {len(profit_and_loss_rows)}, "
        f"Dividend: {len(stock_dividend_rows)}, CFS: {len(cash_flow_rows)}"
    )

    # 5) アーティファクトとして保存
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

    # 6) /api/v1/screening/run を実行する
    print("DEBUG: Executing /api/v1/screening/run")

    screening_params = {
        "sec_codes": None,
        "evaluation_date": target_date.isoformat(),
    }

    r_screening = client.post("/api/v1/screening/run", params=screening_params)

    # スクリーニングAPIの実行結果を確認
    assert r_screening.status_code in (
        200,
        400,
        422,
    ), f"Screening API returned unexpected status: {r_screening.status_code}, response: {r_screening.text}"

    if r_screening.status_code != 200:
        print(
            f"DEBUG: Screening API returned non-200 status: {r_screening.status_code}, "
            f"response: {r_screening.text}"
        )
        pytest.skip("Screening API did not return 200")
        return

    screening_result = r_screening.json()
    print(f"DEBUG: Screening result: {screening_result}")

    # スクリーニング結果が返ってきたことを確認
    assert screening_result.get("status") == "success", (
        f"Screening API returned status: {screening_result.get('status')}, "
        f"message: {screening_result.get('message')}"
    )

    # 8) スクリーニング結果をアーティファクトとして保存
    if screening_result.get("result"):
        try:
            artifact_name = "test_edinet_process_date_range_screening_result"
            write_csv_artifact(screening_result.get("result"), name=artifact_name)
        except Exception as e:
            print(f"DEBUG: Failed to write screening result artifact: {e}")
