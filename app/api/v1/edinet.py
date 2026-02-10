"""EDINET 貸借対照表取得API.

EDINET APIを利用した貸借対照表データの取得・保存エンドポイントを提供します。
バッチ管理テーブルは使用せず、同期的にレスポンスを返します。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.services import get_edinet_balance_sheet_service
from app.schemas.batch import EdinetBalanceSheetRequest, EdinetBalanceSheetResponse
from app.services.market_data.edinet.balance_sheet.service import EdinetBalanceSheetService

router = APIRouter(tags=["edinet"])

logger = logging.getLogger(__name__)


@router.post("/balance-sheet", response_model=EdinetBalanceSheetResponse)
async def run_edinet_balance_sheet_batch(
    request: EdinetBalanceSheetRequest,
    service: EdinetBalanceSheetService = Depends(get_edinet_balance_sheet_service),
):
    """EDINET 貸借対照表を一括取得します.

    指定期間の有価証券報告書を検索し、各書類から5年分の貸借対照表データを取得・保存します。
    処理は同期的に実行され、完了後にレスポンスを返します。

    Args:
        request: バッチ実行リクエスト（開始日、終了日、進捗更新間隔、最大ドキュメント数）
        service: EDINET 貸借対照表サービス

    Returns:
        EdinetBalanceSheetResponse: 処理結果
    """
    logger.info(
        "Starting EDINET balance sheet fetch: %s to %s",
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

    try:
        result = await service.fetch_multiple_balance_sheets(
            start_date=start_date,
            end_date=end_date,
            progress_interval=request.progress_interval or 10,
            max_documents=request.max_documents,
        )

        # job_idは同期実行のため、タイムスタンプベースの固定値
        job_id = f"sync-{datetime.now(timezone.utc).isoformat()}"

        response = EdinetBalanceSheetResponse(
            job_id=job_id,
            status=result.get("status", "completed"),
            total_documents=result.get("total_documents", 0),
            processed_documents=result.get("processed_documents", 0),
            saved_years=result.get("saved_years", 0),
            failed_documents=result.get("failed_documents", 0),
        )

        logger.info("EDINET balance sheet fetch completed: %s", response.model_dump())
        return response

    except Exception as e:
        logger.exception("EDINET balance sheet fetch failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch EDINET balance sheets: {str(e)}",
        ) from e
