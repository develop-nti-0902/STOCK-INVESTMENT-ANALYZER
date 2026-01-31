import csv
import json
import os
import shutil
from datetime import date

import pytest

from app.repositories.edinet_balance_sheet_repository import (
    EdinetBalanceSheetRepository,
)
from app.services.market_data.edinet.balance_sheet.fetcher import (
    EdinetDocumentFetcher,
)
from app.services.market_data.edinet.balance_sheet.parser import (
    EdinetBalanceSheetParser,
)
from app.services.market_data.edinet.common.api_client import EdinetAPIClient
from app.utils.database import get_session_maker


@pytest.mark.asyncio
async def test_fetch_parse_and_save_end_to_end_real(tmp_path):
    """実ネットワークでEDINETからダウンロードし、DBへUPSERTする統合テスト。

    前提:
        - 環境変数 `EDINET_SUBSCRIPTION_KEY` が設定されていること
        - DB接続の環境変数が設定されていること
            （例:
             APP_NAME, APP_VERSION, DB_HOST, DB_PORT,
             DB_NAME, DB_USER, DB_PASSWORD 等）
    """
    # Try env var first, then .env file in repo root
    subscription_key = os.environ.get("EDINET_SUBSCRIPTION_KEY")
    if not subscription_key:
        env_path = os.path.join(os.getcwd(), ".env")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as fh:
                    for ln in fh:
                        if ln.strip().startswith("EDINET_SUBSCRIPTION_KEY"):
                            # parse KEY=VALUE (allow spaces)
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

    # 指定日 2025-06-25 の書類を検索（テスト対象データが存在することを前提）
    client = EdinetAPIClient()
    d = date(2025, 6, 25)
    docs = await client.search_documents(d)
    # If remote API is unreachable or returns no results in this environment,
    # fall back to local sample data shipped in
    # `work/edinet_api_test/data.json`.
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

    assert docs, "No EDINET documents found for 2025-06-25"

    # doc 選定: secCode が存在し、かつ有価証券報告書（受益証券を除く）を抽出
    doc = None
    for item in docs:
        sec_code = item.get("secCode")
        doc_desc = item.get("docDescription", "")
        # 有価証券報告書で、受益証券でないもの
        if (
            sec_code
            and "有価証券報告書" in doc_desc
            and "受益証券" not in doc_desc
        ):
            doc = item
            break
    assert doc, "No securities report (有価証券報告書) with secCode found"

    doc_id = doc.get("docID") or doc.get("docId") or doc.get("doc_id")
    sec_code = doc.get("secCode")
    submission_date_str = doc.get("submitDate") or doc.get("submissionDate")
    submission_date = (
        date.fromisoformat(submission_date_str)
        if submission_date_str
        else date.today()
    )

    # ダウンロード（バイト列）
    zip_bytes = await client.download_document(
        doc_id, subscription_key=subscription_key
    )

    # 一時ファイルに書き込み・展開
    fetcher = EdinetDocumentFetcher(api_client=client, work_dir=tmp_path)
    xbrl_path = await fetcher._write_and_extract(doc_id, zip_bytes)

    # Debug: copy extracted XBRL to repo for inspection
    try:
        artifact_dir = os.path.join(
            os.getcwd(),
            "tests",
            "integration",
            "services",
            "edinet",
            "balance_sheet",
            "artifact",
        )
        os.makedirs(artifact_dir, exist_ok=True)
        extracted_dest = os.path.join(
            artifact_dir, f"extracted_{sec_code}.xbrl"
        )
        shutil.copy(str(xbrl_path), extracted_dest)
        print(f"Copied extracted XBRL to {extracted_dest}")
    except Exception as e:
        print("Failed to copy extracted XBRL:", e)

    parser = EdinetBalanceSheetParser()
    parsed = parser.parse(str(xbrl_path))

    # Debug: dump parsed output to repo for inspection
    debug_out = os.path.join(artifact_dir, f"parsed_{sec_code}.json")
    try:
        with open(debug_out, "w", encoding="utf-8") as fh:
            json.dump(parsed, fh, ensure_ascii=False, indent=2, default=str)
        print(f"Wrote parsed JSON to {debug_out}")
    except Exception as e:
        print("Failed to write parsed JSON:", e)

    # current 年度を利用
    current = parsed.get("current") or {}
    period_end = current.get("period_end")
    assert period_end, "Parsed data missing period_end"

    payload = {
        "doc_id": doc_id,
        "sec_code": sec_code,
        "filer_name": doc.get("filerName"),
        "submission_date": submission_date,
        "period_end_date": period_end,
        "fiscal_year": (
            int(str(period_end).split("-")[0]) if period_end else None
        ),
        "report_type": "annual",
        "total_assets": current.get("assets"),
        "total_liabilities": current.get("liabilities"),
        "total_equity": current.get("equity"),
        "is_consolidated": current.get("consolidation"),
    }

    # DB に接続して実際に upsert を実施
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = EdinetBalanceSheetRepository(session)
        res = await repo.upsert(payload)
        await session.commit()

    # 検証: upsert 後にレコードが取得できること
    assert res is not None
    assert getattr(res, "doc_id", None) == doc_id
    assert getattr(res, "sec_code", None) == sec_code

    # DB に格納されたレコードを CSV に書き出す
    period_end_str = (
        period_end.isoformat()
        if hasattr(period_end, "isoformat")
        else str(period_end)
    )
    out_dir = artifact_dir
    csv_path = os.path.join(out_dir, f"edinet_{sec_code}_{period_end_str}.csv")
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
        writer.writerow(
            [
                getattr(res, "doc_id", ""),
                getattr(res, "sec_code", ""),
                getattr(res, "filer_name", ""),
                getattr(res, "submission_date", ""),
                getattr(res, "period_end_date", ""),
                getattr(res, "fiscal_year", ""),
                getattr(res, "report_type", ""),
                getattr(res, "total_assets", ""),
                getattr(res, "total_liabilities", ""),
                getattr(res, "total_equity", ""),
                getattr(res, "is_consolidated", ""),
            ]
        )
    print(f"Wrote DB record CSV to {csv_path}")
