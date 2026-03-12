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
from app.services.data_synchronization.market_data.edinet.update_service import (
    EdinetAggregateUpdateService,
)
from app.utils.database import get_db

# The batch endpoints that used to call per-service orchestration methods
# have been removed in favor of the centralized update API
# (`EdinetAggregateUpdateService`). If you need to expose batch endpoints,
# call the appropriate update service directly.

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

    以下の処理を垢列実行:
    1. 指定期間の訪文日仁写を EDINET API から検索
    2. 各ドキュメントをダウンロード〉XBRL 解析
    3. 複数の訪文シート（各種計算書）を抽出・保存

        **関連テーブル:**
        - 書込/UPSERT:
            - `edinet_document`
            - `edinet_profit_and_loss`
            - `edinet_balance_sheet`
            - `edinet_cash_flow_statement`
            - `edinet_stock_dividend`
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
