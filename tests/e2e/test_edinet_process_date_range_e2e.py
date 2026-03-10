"""E2Eテスト: EDINET 日付範囲バッチ処理API.

このテストは実際のEDINET APIを呼び出すため、ネットワーク接続が必要です。
テスト実行時間を短縮するため、max_documentsを制限しています。

テストは以下の5つに分割：
1. test_setup_stock_master_for_edinet - マスタ更新
2. test_edinet_process_date_range_triggers_api - API実行確認
3. test_edinet_process_date_range_saves_to_db_profit_and_loss - P&L確認
4. test_edinet_process_date_range_saves_to_db_dividends - 配当確認
5. test_edinet_process_date_range_saves_to_db_cash_flow - キャッシュフロー確認
"""

# flake8: noqa

from datetime import date

import pytest

from app.models.market_data.edinet import (
    EdinetBalanceSheet,
    EdinetCashFlowStatement,
    EdinetDocument,
    EdinetProfitAndLoss,
    EdinetStockDividend,
)
from app.models.market_data.stock_master import StockMaster
from app.repositories.market_data.edinet import (
    EdinetBalanceSheetRepository,
    EdinetCashFlowStatementRepository,
    EdinetProfitAndLossRepository,
    EdinetStockDividendRepository,
)
from app.repositories.market_data.stock_master import StockMasterRepository
from tests.e2e.utils import (
    assert_artifact_written,
    cleanup_repository_delete_all,
    cleanup_table,
    fetch_edinet_balance_sheet_rows,
    fetch_edinet_cash_flow_statement_rows,
    fetch_edinet_document_rows,
    fetch_edinet_profit_and_loss_rows,
    fetch_edinet_stock_dividend_rows,
    fetch_stock_master_for_artifact,
    run_async_safely,
    verify_edinet_balance_sheet_has_data,
    verify_edinet_cash_flow_statement_has_data,
    verify_edinet_profit_and_loss_has_data,
    verify_edinet_stock_dividend_has_data,
    verify_stock_master_has_data,
    write_csv_artifact,
)

# Ensure all e2e tests run on the same xdist worker (loadgroup)
pytestmark = pytest.mark.xdist_group("e2e")


def test_setup_stock_master_for_edinet(client):
    """Setup: EDINET 処理用の stock_master を更新する.

    手順:
    1. StockMaster テーブルをクリーンアップ
    2. /api/v1/stock-master/fetch で全データ取得
    3. DB に格納されたことを確認（存在確認のみ）
    """
    # 事前クリーンアップ
    cleanup_table(StockMaster)

    # 1. stock_master を全取得（EDINET処理に必須）
    r_fetch = client.post("/api/v1/stock-master/fetch")
    assert r_fetch.status_code == 200, f"Unexpected status: {r_fetch.status_code}"

    # 2. DB に格納されたことを確認（存在確認のみ）
    has_data = verify_stock_master_has_data()
    assert has_data, "Setup failed: stock_master テーブルに格納されたデータが見つかりません"


@pytest.mark.slow
def test_edinet_process_date_range_triggers_api(client):
    """API: EDINET process-date-range API を実行してレスポンスを確認.

    手順:
    1. 前提条件確認（stock_master が存在）
    2. POST /api/v1/edinet/process-date-range でバッチ実行
    3. レスポンス構造を確認
    """
    # 前提条件確認
    has_data = verify_stock_master_has_data()
    assert has_data, "Precondition: stock_master に格納されたデータが必要です"

    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 10,
        "progress_interval": 1,
        "transaction_atomic": True,
    }

    # API実行
    r_batch = client.post("/api/v1/edinet/process-date-range", params=params)

    # 処理が正常に完了するか、もしくはデータが見つからない場合も許容
    assert r_batch.status_code in (
        200,
        400,
        422,
    ), f"Unexpected status code: {r_batch.status_code}, response: {r_batch.text}"

    if r_batch.status_code != 200:
        pytest.skip("EDINET did not return 200, possibly no data available")
        return

    batch_result = r_batch.json()

    # レスポンス構造確認
    assert isinstance(batch_result, dict), "Response should be a dictionary"
    assert "status" in batch_result, "Response should contain status"
    assert "total_documents" in batch_result, "Response should contain total_documents"
    assert "processed_documents" in batch_result, "Response should contain processed_documents"
    assert "saved_items" in batch_result, "Response should contain saved_items"
    assert "failed_documents" in batch_result, "Response should contain failed_documents"

    # データが見つからない場合は早期リターン
    if batch_result.get("total_documents", 0) == 0:
        pytest.skip("No documents found by EDINET API in the specified period")
        return

    # ドキュメント処理がすべて失敗した場合は異常として扱う
    if batch_result.get("failed_documents", 0) > 0 and batch_result.get("saved_items", 0) == 0:
        assert False, (
            f"All documents failed (異常):\\n"
            f"  Total: {batch_result.get('total_documents')}\\n"
            f"  Failed: {batch_result.get('failed_documents')}\\n"
            f"  Saved: {batch_result.get('saved_items')}\\n"
            f"  Status: {batch_result.get('status')}\\n"
            f"  Results: {batch_result.get('results')}"
        )


@pytest.mark.slow
def test_edinet_process_date_range_saves_to_db_profit_and_loss(client):
    """DB確認: EDINET 処理で損益計算書（P&L）が DB に格納されることを確認.

    手順:
    1. EdinetProfitAndLoss テーブルをクリーンアップ
    2. /api/v1/edinet/process-date-range でバッチ実行
    3. DB に損益計算書レコードが格納されたことを確認（存在確認のみ）
    """
    # テーブルクリーンアップ
    cleanup_table(EdinetProfitAndLoss)
    cleanup_table(EdinetDocument)

    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 10,
        "progress_interval": 1,
        "transaction_atomic": True,
    }

    # API実行
    r_batch = client.post("/api/v1/edinet/process-date-range", params=params)

    if r_batch.status_code != 200:
        pytest.skip("EDINET API did not return 200")
        return

    batch_result = r_batch.json()
    if batch_result.get("total_documents", 0) == 0:
        pytest.skip("No documents found by EDINET API")
        return

    if batch_result.get("failed_documents", 0) > 0 and batch_result.get("saved_items", 0) == 0:
        assert False, (
            f"All documents failed (異常):\\n"
            f"  Total: {batch_result.get('total_documents')}\\n"
            f"  Failed: {batch_result.get('failed_documents')}\\n"
            f"  Saved: {batch_result.get('saved_items')}\\n"
            f"  Status: {batch_result.get('status')}"
        )

    # DB確認（存在確認のみ）
    has_data = verify_edinet_profit_and_loss_has_data()
    assert has_data, "DB確認失敗: EdinetProfitAndLoss テーブルにレコードが見つかりません"

    # artifact 出力（必須）
    profit_and_loss_rows = run_async_safely(fetch_edinet_profit_and_loss_rows())
    assert profit_and_loss_rows, "No P&L data to write artifact"
    artifact_name = "edinet_profit_and_loss_artifact"
    write_csv_artifact(profit_and_loss_rows, name=artifact_name)
    assert_artifact_written(artifact_name)


@pytest.mark.slow
def test_edinet_process_date_range_saves_to_db_dividends(client):
    """DB確認: EDINET 処理で配当（Dividend）が DB に格納されることを確認.

    手順:
    1. EdinetStockDividend テーブルをクリーンアップ
    2. /api/v1/edinet/process-date-range でバッチ実行
    3. DB に配当レコードが格納されたことを確認（存在確認のみ）
    """
    # テーブルクリーンアップ
    cleanup_table(EdinetStockDividend)
    cleanup_table(EdinetDocument)

    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 10,
        "progress_interval": 1,
        "transaction_atomic": True,
    }

    # API実行
    r_batch = client.post("/api/v1/edinet/process-date-range", params=params)

    if r_batch.status_code != 200:
        pytest.skip("EDINET API did not return 200")
        return

    batch_result = r_batch.json()
    if batch_result.get("total_documents", 0) == 0:
        pytest.skip("No documents found by EDINET API")
        return

    if batch_result.get("failed_documents", 0) > 0 and batch_result.get("saved_items", 0) == 0:
        assert False, (
            f"All documents failed (異常):\\n"
            f"  Total: {batch_result.get('total_documents')}\\n"
            f"  Failed: {batch_result.get('failed_documents')}\\n"
            f"  Saved: {batch_result.get('saved_items')}\\n"
            f"  Status: {batch_result.get('status')}"
        )

    # DB確認（存在確認のみ）
    has_data = verify_edinet_stock_dividend_has_data()
    assert has_data, "DB確認失敗: EdinetStockDividend テーブルにレコードが見つかりません"

    # artifact 出力（必須）
    dividend_rows = run_async_safely(fetch_edinet_stock_dividend_rows())
    assert dividend_rows, "No dividend data to write artifact"
    artifact_name = "edinet_dividend_artifact"
    write_csv_artifact(dividend_rows, name=artifact_name)
    assert_artifact_written(artifact_name)


@pytest.mark.slow
def test_edinet_process_date_range_saves_to_db_cash_flow(client):
    """DB確認: EDINET 処理でキャッシュフロー（Cash Flow）が DB に格納されることを確認.

    手順:
    1. EdinetCashFlowStatement テーブルをクリーンアップ
    2. /api/v1/edinet/process-date-range でバッチ実行
    3. DB にキャッシュフロー レコードが格納されたことを確認（存在確認のみ）
    """
    # テーブルクリーンアップ
    cleanup_table(EdinetCashFlowStatement)
    cleanup_table(EdinetDocument)

    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 10,
        "progress_interval": 1,
        "transaction_atomic": True,
    }

    # API実行
    r_batch = client.post("/api/v1/edinet/process-date-range", params=params)

    if r_batch.status_code != 200:
        pytest.skip("EDINET API did not return 200")
        return

    batch_result = r_batch.json()
    if batch_result.get("total_documents", 0) == 0:
        pytest.skip("No documents found by EDINET API")
        return

    if batch_result.get("failed_documents", 0) > 0 and batch_result.get("saved_items", 0) == 0:
        assert False, (
            f"All documents failed (異常):\\n"
            f"  Total: {batch_result.get('total_documents')}\\n"
            f"  Failed: {batch_result.get('failed_documents')}\\n"
            f"  Saved: {batch_result.get('saved_items')}\\n"
            f"  Status: {batch_result.get('status')}"
        )

    # DB確認（存在確認のみ）
    has_data = verify_edinet_cash_flow_statement_has_data()
    assert has_data, "DB確認失敗: EdinetCashFlowStatement テーブルにレコードが見つかりません"

    # artifact 出力（必須）
    cash_flow_rows = run_async_safely(fetch_edinet_cash_flow_statement_rows())
    assert cash_flow_rows, "No cash flow data to write artifact"
    artifact_name = "edinet_cash_flow_artifact"
    write_csv_artifact(cash_flow_rows, name=artifact_name)
    assert_artifact_written(artifact_name)

    # edinet_document の artifact も出力（追加）
    edinet_doc_rows = run_async_safely(fetch_edinet_document_rows())
    if edinet_doc_rows:
        write_csv_artifact(edinet_doc_rows, name="edinet_document_artifact")
        assert_artifact_written("edinet_document_artifact")


@pytest.mark.slow
def test_edinet_process_date_range_saves_to_db_balance_sheet(client):
    """DB確認: EDINET 処理で貸借対照表（Balance Sheet）が DB に格納されることを確認.

    手順:
    1. EdinetBalanceSheet テーブルをクリーンアップ
    2. /api/v1/edinet/process-date-range でバッチ実行
    3. DB に貸借対照表レコードが格納されたことを確認（存在確認のみ）
    """
    # テーブルクリーンアップ
    cleanup_table(EdinetBalanceSheet)
    cleanup_table(EdinetDocument)

    target_date = date(2025, 6, 25)

    params = {
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "max_documents": 10,
        "progress_interval": 1,
        "transaction_atomic": True,
    }

    # API実行
    r_batch = client.post("/api/v1/edinet/process-date-range", params=params)

    if r_batch.status_code != 200:
        pytest.skip("EDINET API did not return 200")
        return

    batch_result = r_batch.json()
    if batch_result.get("total_documents", 0) == 0:
        pytest.skip("No documents found by EDINET API")
        return

    if batch_result.get("failed_documents", 0) > 0 and batch_result.get("saved_items", 0) == 0:
        assert False, (
            f"All documents failed (異常):\\n"
            f"  Total: {batch_result.get('total_documents')}\\n"
            f"  Failed: {batch_result.get('failed_documents')}\\n"
            f"  Saved: {batch_result.get('saved_items')}\\n"
            f"  Status: {batch_result.get('status')}"
        )

    # DB確認（存在確認のみ）
    has_data = verify_edinet_balance_sheet_has_data()
    assert has_data, "DB確認失敗: EdinetBalanceSheet テーブルにレコードが見つかりません"

    # artifact 出力（必須）
    balance_sheet_rows = run_async_safely(fetch_edinet_balance_sheet_rows())
    assert balance_sheet_rows, "No balance sheet data to write artifact"
    artifact_name = "edinet_balance_sheet_artifact"
    write_csv_artifact(balance_sheet_rows, name=artifact_name)
    assert_artifact_written(artifact_name)

    # edinet_document の artifact も出力（追加）
    edinet_doc_rows = run_async_safely(fetch_edinet_document_rows())
    if edinet_doc_rows:
        write_csv_artifact(edinet_doc_rows, name="edinet_document_artifact")
        assert_artifact_written("edinet_document_artifact")
