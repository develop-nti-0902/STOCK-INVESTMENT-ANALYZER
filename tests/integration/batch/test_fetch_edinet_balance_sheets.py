from __future__ import annotations

import csv
import json
import os
from datetime import date
from pathlib import Path

import pytest

from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.repositories.edinet_balance_sheet_repository import (
    EdinetBalanceSheetRepository,
)
from app.services.batch.batch_execution_service import BatchExecutionService
from app.services.batch.fetch_edinet_balance_sheets import (
    fetch_edinet_balance_sheets_job,
)
from app.services.market_data.edinet.common.api_client import EdinetAPIClient
from app.utils.database import get_session_maker


@pytest.mark.asyncio
async def test_fetch_edinet_balance_sheets_batch_end_to_end(tmp_path: Path):
    """実ネットワークでEDINETからダウンロードし、DBへ格納するバッチ統合テスト。

    前提:
        - 環境変数 `EDINET_SUBSCRIPTION_KEY` が設定されていること
        - DB接続の環境変数が設定されていること
            （例: APP_NAME, APP_VERSION, DB_HOST, DB_PORT,
             DB_NAME, DB_USER, DB_PASSWORD 等）
    """
    # 環境変数から EDINET_SUBSCRIPTION_KEY を取得
    subscription_key = os.environ.get("EDINET_SUBSCRIPTION_KEY")
    if not subscription_key:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as fh:
                    for ln in fh:
                        if ln.strip().startswith("EDINET_SUBSCRIPTION_KEY"):
                            parts = ln.split("=", 1)
                            if len(parts) == 2:
                                subscription_key = (
                                    parts[1].strip().strip('"').strip("'")
                                )
                                break
            except Exception:
                subscription_key = None
    if not subscription_key:
        pytest.skip("EDINET_SUBSCRIPTION_KEY not found; skipping test")

    # 指定日の書類を検索（2025-06-25 にテストデータが存在することを前提）
    client = EdinetAPIClient()
    test_date = date(2025, 6, 25)
    docs = await client.search_documents(test_date)

    # リモートAPIが利用不可またはデータがない場合、ローカルサンプルデータにフォールバック
    if not docs:
        local_path = os.path.join(
            os.getcwd(), "work", "edinet_api_test", "data.json"
        )
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as fh:
                    local = json.load(fh)
                if isinstance(local, dict) and "results" in local:
                    docs = local["results"]
                elif isinstance(local, list):
                    docs = local
            except Exception:
                docs = []

    if not docs:
        pytest.skip(
            f"No EDINET documents found for {test_date}; skipping test"
        )

    # 有価証券報告書（docTypeCode=120）で、secCodeが存在するものを選定
    annual_report = None
    for item in docs:
        sec_code = item.get("secCode")
        doc_type_code = item.get("docTypeCode")
        doc_desc = item.get("docDescription", "")
        # 有価証券報告書で、受益証券でないもの
        if (
            sec_code
            and doc_type_code == "120"
            and "有価証券報告書" in doc_desc
            and "受益証券" not in doc_desc
        ):
            annual_report = item
            break

    if not annual_report:
        pytest.skip(
            "No valid annual securities report (有価証券報告書) with "
            "secCode found; skipping test"
        )

    # バッチサービスの準備
    session_maker = get_session_maker()
    async with session_maker() as session:
        batch_repo = BatchExecutionRepository(session)
        batch_service = BatchExecutionService(repository=batch_repo)

        # バッチ実行
        # 1日だけの期間で実行し、10件に制限してテストを高速化
        result = await fetch_edinet_balance_sheets_job(
            batch_service=batch_service,
            start_date=test_date,
            end_date=test_date,
            max_documents=10,
        )

        # 結果の検証
        assert result is not None
        assert result["status"] == "completed"
        assert result["total_documents"] > 0
        assert result["processed_documents"] > 0

        # DBに格納されたデータを確認
        edinet_repo = EdinetBalanceSheetRepository(session)
        doc_id = (
            annual_report.get("docID")
            or annual_report.get("docId")
            or annual_report.get("doc_id")
        )
        sec_code = annual_report.get("secCode")

        # doc_id で検索
        records = await edinet_repo.find_by_doc_id(doc_id)
        assert len(records) > 0, f"No records found for doc_id={doc_id}"

        # アーティファクト保存用ディレクトリ
        artifact_dir = os.path.join(
            os.getcwd(),
            "tests",
            "integration",
            "batch",
            "artifact",
        )
        os.makedirs(artifact_dir, exist_ok=True)

        # CSVファイルに書き出し
        csv_path = os.path.join(
            artifact_dir, f"edinet_batch_{sec_code}_{test_date}.csv"
        )
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "doc_id",
                    "sec_code",
                    "filer_name",
                    "submission_date",
                    "period_end_date",
                    "fiscal_year",
                    "report_type",
                    "total_assets",
                    "total_liabilities",
                    "total_equity",
                    "is_consolidated",
                ]
            )
            for record in records:
                writer.writerow(
                    [
                        getattr(record, "doc_id", ""),
                        getattr(record, "sec_code", ""),
                        getattr(record, "filer_name", ""),
                        getattr(record, "submission_date", ""),
                        getattr(record, "period_end_date", ""),
                        getattr(record, "fiscal_year", ""),
                        getattr(record, "report_type", ""),
                        getattr(record, "total_assets", ""),
                        getattr(record, "total_liabilities", ""),
                        getattr(record, "total_equity", ""),
                        getattr(record, "is_consolidated", ""),
                    ]
                )
        print(f"Wrote batch result CSV to {csv_path}")

        # JSONファイルにも結果を書き出し
        json_path = os.path.join(
            artifact_dir, f"edinet_batch_result_{test_date}.json"
        )
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2, default=str)
        print(f"Wrote batch result JSON to {json_path}")
