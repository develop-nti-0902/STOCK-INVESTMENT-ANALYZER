"""EDINET 貸借対照表取得バッチランナー.

このモジュールは `EdinetBalanceSheetService` のバッチ処理を担当します。
`app.services.core.batch.base.BaseBatchRunner` を継承し、ジョブ管理には
`app.services.batch.batch_execution_service.BatchExecutionContext` を利用して
`BatchExecution` テーブルへ記録します。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

from app.services.batch.batch_execution_service import BatchExecutionContext
from app.services.core.batch.base import BaseBatchRunner
from app.services.market_data.edinet.balance_sheet.converter import EdinetBalanceSheetConverter
from app.services.market_data.edinet.balance_sheet.fetcher import EdinetDocumentFetcher
from app.services.market_data.edinet.balance_sheet.file_manager import EdinetFileManager
from app.services.market_data.edinet.balance_sheet.parser import EdinetBalanceSheetParser
from app.services.market_data.edinet.balance_sheet.saver import EdinetBalanceSheetSaver
from app.services.market_data.edinet.balance_sheet.service import EdinetBalanceSheetService
from app.utils.database import get_session_maker
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetBatchRunner(BaseBatchRunner):
    """EDINET 貸借対照表取得バッチランナー.

    指定期間の有価証券報告書を検索し、各書類から5年分のデータを取得・保存します。
    """

    BATCH_TYPE = "edinet_balance_sheet_fetch"

    def __init__(
        self,
        batch_service: Any,
        fetcher: EdinetDocumentFetcher,
        parser: EdinetBalanceSheetParser,
        file_manager: EdinetFileManager,
    ) -> None:
        """初期化.

        Args:
            batch_service: バッチ管理サービス
            fetcher: EDINET ドキュメント取得用のフェッチャ
            parser: EDINET 貸借対照表パーサ
            file_manager: EDINET 一時ファイル管理ユーティリティ
        """
        super().__init__(batch_service=batch_service)
        self.fetcher = fetcher
        self.parser = parser
        self.file_manager = file_manager
        self.session_maker = get_session_maker()

    async def run(self, *args, **kwargs) -> Dict[str, Any]:
        """バッチ実行エントリポイント（BaseBatchRunner の抽象メソッド実装）.

        実際の処理は fetch_balance_sheets() に委譲します。
        """
        return await self.fetch_balance_sheets(*args, **kwargs)

    async def fetch_balance_sheets(
        self,
        start_date: date,
        end_date: date,
        progress_interval: int = 10,
        max_documents: int | None = None,
    ) -> Dict[str, Any]:
        """EDINET 貸借対照表を取得するバッチ処理.

        Args:
            start_date: 検索開始日
            end_date: 検索終了日
            progress_interval: 進捗更新の間隔（処理ドキュメント数、デフォルト: 10）
            max_documents: 処理する最大ドキュメント数（Noneの場合は全件処理）

        Returns:
            処理結果を含む辞書
        """
        ##########################################################
        # 入力引数の正規化（run 経由で呼び出された場合の変換処理）
        ##########################################################
        if isinstance(start_date, dict):
            kwargs = start_date
            start_date = kwargs.get("start_date")
            end_date = kwargs.get("end_date")
            progress_interval = kwargs.get("progress_interval", 10)
            max_documents = kwargs.get("max_documents")

        ##########################################################
        # 引数チェック（start_date, end_date は必須）
        ##########################################################
        if not start_date or not end_date:
            raise ValueError("start_date and end_date are required")

        async with BatchExecutionContext(
            self.batch_service,
            job_type=self.BATCH_TYPE,
            params={
                "start_date": str(start_date),
                "end_date": str(end_date),
                "max_documents": max_documents,
            },
        ) as ctx:
            try:
                ##########################################################
                # 書類検索（EDINET API 呼び出し）
                ##########################################################
                documents = await self._search_documents(start_date, end_date)

                ##########################################################
                # ドキュメント件数制限（max_documents によるトリミング）
                ##########################################################
                if max_documents is not None and len(documents) > max_documents:
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

                ##########################################################
                # バッチ実行用統計変数の初期化
                ##########################################################
                processed_docs = 0
                saved_years_count = 0
                failed_docs = 0

                for i, doc in enumerate(documents, start=1):
                    ##########################################################
                    # ドキュメントメタ情報の抽出
                    ##########################################################
                    doc_id = doc.get("docID")
                    sec_code = doc.get("secCode")
                    submission_date_str = doc.get("submitDateTime", "")
                    filer_name = doc.get("filerName")

                    if not doc_id:
                        logger.warning("Document missing docID: %s", doc)
                        failed_docs += 1
                        continue

                    ##########################################################
                    # 提出日（submission_date）の解析
                    ##########################################################
                    try:
                        # submitDateTime は "YYYY-MM-DD HH:MM" 形式を想定
                        submission_date = date.fromisoformat(submission_date_str.split(" ")[0])
                    except Exception:
                        logger.warning(
                            "Invalid submission_date for doc_id=%s: %s",
                            doc_id,
                            submission_date_str,
                        )
                        submission_date = start_date  # フォールバック

                    ##########################################################
                    # ドキュメントからの財務情報取得と保存（5年分）
                    ##########################################################
                    try:
                        ##########################################################
                        # secCode の存在チェック
                        ##########################################################
                        if sec_code is None:
                            logger.warning(
                                "Missing secCode for doc_id=%s: %s",
                                doc_id,
                                doc,
                            )
                            failed_docs += 1
                            continue

                        ##########################################################
                        # DB セッション生成とトランザクション管理
                        ##########################################################
                        async with self.session_maker() as session:  # type: ignore[call-arg]
                            try:
                                ##########################################################
                                # サービス初期化（コンバータ・セーバー・サービス）
                                ##########################################################
                                converter = EdinetBalanceSheetConverter()
                                saver = EdinetBalanceSheetSaver(session=session)
                                edinet_service = EdinetBalanceSheetService(
                                    fetcher=self.fetcher,
                                    parser=self.parser,
                                    converter=converter,
                                    saver=saver,
                                    file_manager=self.file_manager,
                                )
                                results = await edinet_service.fetch_and_save(
                                    doc_id=doc_id,
                                    sec_code=sec_code,
                                    submission_date=submission_date,
                                    filer_name=filer_name,
                                )

                                ##########################################################
                                # 結果反映（コミット、統計更新、ログ出力）
                                ##########################################################
                                await session.commit()
                                saved_years_count += len(results) if results else 0
                                processed_docs += 1
                                logger.info(
                                    "Processed doc_id=%s, saved %d years",
                                    doc_id,
                                    len(results) if results else 0,
                                )
                            except Exception as e:
                                await session.rollback()
                                logger.exception("Failed to process doc_id=%s: %s", doc_id, e)
                                failed_docs += 1
                    except Exception as e:
                        logger.exception("Failed to create session for doc_id=%s: %s", doc_id, e)
                        failed_docs += 1

                    ##########################################################
                    # 定期進捗更新（BatchExecution の更新）
                    ##########################################################
                    if i % progress_interval == 0:
                        await ctx.update_progress(
                            processed=processed_docs,
                            total=total_docs,
                            failed=failed_docs,
                        )

                ##########################################################
                # 最終進捗更新と結果作成
                ##########################################################
                await ctx.update_progress(
                    processed=processed_docs,
                    total=total_docs,
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

    async def _search_documents(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """指定期間内の有価証券報告書を検索する.

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

        ##########################################################
        # 指定期間の日次検索ループ（EDINET API は日付単位）
        ##########################################################
        while current_date <= end_date:
            try:
                docs = await self.fetcher.search_documents(current_date)
                ##########################################################
                # 書類フィルタリング（有価証券報告書のみ、受益証券除外、secCode 必須）
                ##########################################################
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
                logger.warning("Failed to search documents for %s: %s", current_date, e)

            current_date += timedelta(days=1)

        logger.info("Total annual reports found: %d", len(all_documents))
        return all_documents


__all__ = ["EdinetBalanceSheetBatchRunner"]
