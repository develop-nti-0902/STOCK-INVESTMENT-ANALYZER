"""EDINET バッチ実行API. EDINET関連のバッチジョブを提供します."""

from __future__ import annotations

import asyncio as _asyncio
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.repositories import get_batch_execution_repository
from app.api.dependencies.services import get_edinet_balance_sheet_batch_runner
from app.repositories.batch_execution_repository import BatchExecutionRepository
from app.schemas.batch import EdinetBalanceSheetRequest, EdinetBalanceSheetResponse
from app.services.market_data.edinet.balance_sheet.batch import EdinetBalanceSheetBatchRunner

router = APIRouter(tags=["edinet"])

logger = logging.getLogger(__name__)


async def _await_pending_tasks(
    pending_tasks: set[_asyncio.Task], context: str | None = None
) -> None:
    """保留中の非同期タスクを待機して例外をログに記録するヘルパー.

    Args:
        pending_tasks (set[_asyncio.Task]): 待機対象のタスク集合
        context (Optional[str]): ログ出力時の任意コンテキスト

    Returns:
        None
    """
    if not pending_tasks:
        return

    try:
        pending_list = list(pending_tasks)
        await _asyncio.gather(*pending_list, return_exceptions=True)
    except Exception:
        if context:
            logger.exception("Error %s", context)
        else:
            logger.exception("Error while awaiting pending progress tasks")
    finally:
        pending_tasks.clear()


@router.post("/balance-sheet", response_model=EdinetBalanceSheetResponse)
async def run_edinet_balance_sheet_batch(
    request: EdinetBalanceSheetRequest,
    batch_runner: EdinetBalanceSheetBatchRunner = Depends(get_edinet_balance_sheet_batch_runner),
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    """EDINET 貸借対照表取得バッチを実行します.

    指定期間の有価証券報告書を検索し、各書類から5年分の貸借対照表データを取得・保存します。

    Args:
        request: バッチ実行リクエスト（開始日、終了日、進捗更新間隔、最大ドキュメント数）
        batch_runner: EDINET 貸借対照表バッチランナー
        repo: バッチ実行リポジトリ

    Returns:
        EdinetBalanceSheetResponse: バッチ実行結果
    """
    logger.info(
        "Starting EDINET balance sheet batch: %s to %s",
        request.start_date,
        request.end_date,
    )

    try:
        start_date = date.fromisoformat(request.start_date)
        end_date = date.fromisoformat(request.end_date)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid date format: {str(e)}",
        ) from e

    pending_tasks: set[_asyncio.Task] = set()

    try:
        result = await batch_runner.fetch_balance_sheets(
            start_date=start_date,
            end_date=end_date,
            progress_interval=request.progress_interval or 10,
            max_documents=request.max_documents,
        )

        await _await_pending_tasks(pending_tasks, "waiting for EDINET batch progress updates")

        job_executions = await repo.get_by_job_type("edinet_balance_sheet_fetch")
        latest_job = job_executions[0] if job_executions else None

        response = EdinetBalanceSheetResponse(
            job_id=str(latest_job.id) if latest_job else "unknown",
            status=result.get("status", "completed"),
            total_documents=result.get("total_documents", 0),
            processed_documents=result.get("processed_documents", 0),
            saved_years=result.get("saved_years", 0),
            failed_documents=result.get("failed_documents", 0),
        )

        logger.info("EDINET balance sheet batch completed: %s", response.model_dump())
        return response

    except Exception as e:
        logger.exception("EDINET balance sheet batch failed: %s", e)
        await _await_pending_tasks(pending_tasks, "waiting for progress tasks after EDINET failure")
        raise
