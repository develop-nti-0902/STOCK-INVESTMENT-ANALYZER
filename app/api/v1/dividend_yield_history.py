"""配当利回り履歴 API エンドポイント."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from app.api.dependencies.services import get_dividend_yield_history_service
from app.exceptions.business import ServiceError
from app.schemas.dividend_yield_history import (
    GenerateDividendYieldHistoryRequest,
    GenerateDividendYieldHistoryResponse,
)
from app.services.data_synchronization.market_data.dividend_yield_history import (
    DividendYieldHistoryService,
)

if TYPE_CHECKING:
    pass

router = APIRouter(tags=["dividend-yield-history"])


@router.post(
    "/generate",
    response_model=GenerateDividendYieldHistoryResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Generate dividend yield history (synchronous)",
)
async def generate_dividend_yield_history(
    request: GenerateDividendYieldHistoryRequest,
    service: DividendYieldHistoryService = Depends(get_dividend_yield_history_service),
) -> GenerateDividendYieldHistoryResponse:
    """配当利回り履歴を同期実行で生成・保存します。

    指定日付で:
    1. 理緡情報（EDINET）から配当を取得
    2. 株価データから等妨栽量を取得
    3. 配当利回りを計算
    4. 結果を保存

        **関連テーブル:**
        - 読取:
            - `stock_master`
            - `stock_code_mapping`
            - `edinet_stock_dividend`
            - `edinet_document`
            - `stocks_1d`
        - 書込:
            - `dividend_yield_history`

    Args:
        request: GenerateDividendYieldHistoryRequest
        service: DividendYieldHistoryService（依存性注入）

    Returns:
        GenerateDividendYieldHistoryResponse

    Raises:
        HTTPException: 400(バリデーション) | 500(内部エラー)
    """
    # target_date の検証（未来日チェック）
    today = date.today()
    if request.target_date > today:
        error_msg = (
            "target_date must not be a future date. " + f"got={request.target_date}, today={today}"
        )
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    try:
        result = await service.generate_for_date(request.target_date)

        # ステータスを決定
        if result.error_count > 0:
            status_str = "partial_error"
        elif result.rowcount == 0 and result.skipped_count == 0:
            status_str = "no_data"
        else:
            status_str = "completed"

        return GenerateDividendYieldHistoryResponse(
            status=status_str,
            rowcount=result.rowcount,
            skipped_count=result.skipped_count,
            error_count=result.error_count,
            message=result.message,
        )

    except ServiceError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service error: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


__all__ = ["router"]
