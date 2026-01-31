from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

from app.services.batch.batch_execution_service import (
    BatchExecutionContext,
    BatchExecutionService,
)
from app.services.market_data.edinet.balance_sheet.fetcher import (
    EdinetDocumentFetcher,
)
from app.services.market_data.edinet.balance_sheet.file_manager import (
    EdinetFileManager,
)
from app.services.market_data.edinet.balance_sheet.parser import (
    EdinetBalanceSheetParser,
)
from app.services.market_data.edinet.balance_sheet.service import (
    EdinetBalanceSheetService,
)
from app.services.market_data.edinet.common.api_client import EdinetAPIClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FetchEdinetBalanceSheetsJob:
    """EDINET 貸借対照表を取得するバッチジョブ。

    指定期間の有価証券報告書を検索し、各書類から5年分のデータを取得・保存します。
    """

    BATCH_TYPE = "edinet_balance_sheet_fetch"

    def __init__(
        self,
        batch_service: BatchExecutionService,
        edinet_service: EdinetBalanceSheetService,
        fetcher: EdinetDocumentFetcher,
    ) -> None:
        self.batch_service = batch_service
        self.edinet_service = edinet_service
        self.fetcher = fetcher

    async def execute(
        self,
        start_date: date,
        end_date: date,
        progress_interval: int = 10,
        max_documents: int | None = None,
    ) -> Dict[str, Any]:
        """バッチ実行のメインロジック。

        Args:
            start_date: 検索開始日
            end_date: 検索終了日
            progress_interval: 進捗更新の間隔（処理ドキュメント数）
            max_documents: 処理する最大ドキュメント数（Noneの場合は全件処理）

        Returns:
            処理結果を含む辞書
        """
        async with BatchExecutionContext(
            self.batch_service, job_type=self.BATCH_TYPE
        ) as ctx:
            try:
                documents = await self._search_documents(start_date, end_date)
                # max_documentsが指定されている場合は制限
                if (
                    max_documents is not None
                    and len(documents) > max_documents
                ):
                    documents = documents[:max_documents]
                    logger.info(
                        "Limited to %d documents (out of %d found)",
                        max_documents,
                        len(documents),
                    )
                total_docs = len(documents)
                logger.info(
                    "Found %d documents between %s and %s",
                    total_docs,
                    start_date,
                    end_date,
                )

                if total_docs == 0:
                    return {
                        "status": "completed",
                        "total_documents": 0,
                        "processed_documents": 0,
                        "saved_years": 0,
                        "failed_documents": 0,
                    }

                processed_docs = 0
                saved_years_count = 0
                failed_docs = 0

                for i, doc in enumerate(documents, start=1):
                    doc_id = doc.get("docID")
                    sec_code = doc.get("secCode")
                    submission_date_str = doc.get("submitDateTime", "")
                    filer_name = doc.get("filerName")

                    # _search_documents で既に secCode をフィルタ済みだが念のため確認
                    if not doc_id:
                        logger.warning("Document missing docID: %s", doc)
                        failed_docs += 1
                        continue

                    # submission_date の解析
                    try:
                        # submitDateTime は "YYYY-MM-DD HH:MM" 形式を想定
                        submission_date = date.fromisoformat(
                            submission_date_str.split(" ")[0]
                        )
                    except Exception:
                        logger.warning(
                            "Invalid submission_date for doc_id=%s: %s",
                            doc_id,
                            submission_date_str,
                        )
                        submission_date = start_date  # フォールバック

                    # 各文書から5年分のデータを取得・保存
                    try:
                        # sec_code は None でないことが期待されるが、static checker
                        # に対処するため明示的に確認する
                        if sec_code is None:
                            logger.warning(
                                "Missing secCode for doc_id=%s: %s",
                                doc_id,
                                doc,
                            )
                            failed_docs += 1
                            continue

                        results = (
                            await self.edinet_service.fetch_and_save_single(
                                doc_id=doc_id,
                                sec_code=sec_code,
                                submission_date=submission_date,
                                filer_name=filer_name,
                            )
                        )
                        saved_years_count += len(results) if results else 0
                        processed_docs += 1
                        logger.info(
                            "Processed doc_id=%s, saved %d years",
                            doc_id,
                            len(results) if results else 0,
                        )
                    except Exception as e:
                        logger.exception(
                            "Failed to process doc_id=%s: %s", doc_id, e
                        )
                        failed_docs += 1

                    # 進捗更新
                    if i % progress_interval == 0:
                        await ctx.update_progress(
                            processed=processed_docs,
                            failed=failed_docs,
                        )

                # 最終的な進捗更新
                await ctx.update_progress(
                    processed=processed_docs,
                    failed=failed_docs,
                )

                result = {
                    "status": "completed",
                    "total_documents": total_docs,
                    "processed_documents": processed_docs,
                    "saved_years": saved_years_count,
                    "failed_documents": failed_docs,
                }
                logger.info("Batch completed: %s", result)
                return result

            except Exception as e:
                logger.exception("Batch execution failed: %s", e)
                raise

    async def _search_documents(
        self, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """指定期間内の有価証券報告書を検索する。

        EDINET API は1日単位でしか検索できないため、
        期間内の全日付をループして書類を取得します。

        Args:
            start_date: 検索開始日
            end_date: 検索終了日

        Returns:
            書類情報のリスト（受益証券を除く）
        """
        all_documents: List[Dict[str, Any]] = []
        current_date = start_date

        while current_date <= end_date:
            try:
                docs = await self.fetcher.search_documents(current_date)
                # 有価証券報告書のみフィルタ（docTypeCode=120）
                # かつ受益証券を除外（内国投資信託受益証券など）
                # かつ secCode が存在するもののみ
                annual_reports = [
                    doc
                    for doc in docs
                    if doc.get("docTypeCode") == "120"
                    and doc.get("secCode") is not None
                    and "受益証券" not in doc.get("docDescription", "")
                ]
                all_documents.extend(annual_reports)
                logger.debug(
                    "Found %d annual reports on %s",
                    len(annual_reports),
                    current_date,
                )
            except Exception as e:
                logger.warning(
                    "Failed to search documents for %s: %s", current_date, e
                )

            current_date += timedelta(days=1)

        logger.info("Total annual reports found: %d", len(all_documents))
        return all_documents


async def fetch_edinet_balance_sheets_job(
    batch_service: BatchExecutionService,
    start_date: date,
    end_date: date,
    max_documents: int | None = None,
) -> Dict[str, Any]:
    """EDINET 貸借対照表取得バッチのエントリポイント。

    Args:
        batch_service: バッチ実行サービス
        start_date: 検索開始日
        end_date: 検索終了日
        max_documents: 処理する最大ドキュメント数（Noneの場合は全件処理）

    Returns:
        処理結果を含む辞書
    """
    # 依存関係の構築
    api_client = EdinetAPIClient()
    work_dir = Path("work/edinet_temp")
    fetcher = EdinetDocumentFetcher(api_client=api_client, work_dir=work_dir)
    parser = EdinetBalanceSheetParser()
    file_manager = EdinetFileManager()

    edinet_service = EdinetBalanceSheetService(
        fetcher=fetcher,
        parser=parser,
        file_manager=file_manager,
    )

    job = FetchEdinetBalanceSheetsJob(
        batch_service=batch_service,
        edinet_service=edinet_service,
        fetcher=fetcher,
    )

    return await job.execute(start_date, end_date, max_documents=max_documents)


__all__ = ["FetchEdinetBalanceSheetsJob", "fetch_edinet_balance_sheets_job"]
