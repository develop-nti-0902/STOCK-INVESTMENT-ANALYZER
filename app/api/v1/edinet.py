"""EDINET 貸借対照表取得API.

EDINET APIを利用した貸借対照表データの取得・保存エンドポイントを提供します。
バッチ管理テーブルは使用せず、同期的にレスポンスを返します。
"""

from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import get_edinet_aggregate_update_service
from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService
from app.utils.database import get_db

# The batch endpoints that used to call per-service orchestration methods
# have been removed in favor of the centralized update API (`EdinetAggregateUpdateService`).
# If you need to expose batch endpoints, call the appropriate update service directly.

router = APIRouter(tags=["edinet"])

logger = logging.getLogger(__name__)


@router.post("/process-date-range")
async def process_date_range(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    start_date: date,
    end_date: date,
    max_documents: int | None = Query(None, ge=1),
    progress_interval: int = Query(10, gt=0),
    transaction_atomic: bool = Query(True),
    service: EdinetAggregateUpdateService = Depends(get_edinet_aggregate_update_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """指定期間の EDINET ドキュメントを検索して処理するバッチを実行します.

    - `start_date` と `end_date` は ISO 日付 (YYYY-MM-DD) で渡してください。
    - `max_documents` を指定すると処理対象数を制限します。
    - 処理は同期的に実行され、完了後に集計結果を返します。
    """
    try:  # pylint: disable=R0913,R0917
        result = await service.process_date_range(
            start_date=start_date,
            end_date=end_date,
            progress_interval=progress_interval,
            max_documents=max_documents,
            session=db,
            transaction_atomic=transaction_atomic,
        )
        return result
    except Exception as exc:
        logger.exception("process_date_range API failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
