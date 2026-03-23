"""レラティブストレングス API エンドポイント."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from app.api.dependencies.services import get_relative_strength_service
from app.schemas.relative_strength import (
    CalculateRelativeStrengthRequest,
    RelativeStrengthAllResponse,
    RelativeStrengthDateResponse,
)
from app.services.data_synchronization.market_data.relative_strength import RelativeStrengthService

router = APIRouter(tags=["relative-strength"])


@router.post(
    "/calculate/date",
    response_model=RelativeStrengthDateResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Calculate RS for all symbols on a specific date",
)
async def calculate_relative_strength_for_date(
    request: CalculateRelativeStrengthRequest,
    service: RelativeStrengthService = Depends(get_relative_strength_service),
) -> RelativeStrengthDateResponse:
    """指定日の全銘柄レラティブストレングスを計算・保存します（バッチ用）."""
    today = date.today()
    if request.target_date > today:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"target_date must not be a future date. got={request.target_date}",
        )

    try:
        result = await service.calculate_for_date(request.target_date)

        if result.error_count > 0:
            status_str = "partial_error"
        elif result.rowcount == 0 and result.skipped_count == 0:
            status_str = "no_data"
        else:
            status_str = "completed"

        return RelativeStrengthDateResponse(
            status=status_str,
            calculation_date=request.target_date.isoformat(),
            rowcount=result.rowcount,
            skipped_count=result.skipped_count,
            error_count=result.error_count,
            message=result.message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post(
    "/calculate/all",
    response_model=RelativeStrengthAllResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Calculate RS for all symbols and all available dates",
)
async def calculate_relative_strength_all(
    service: RelativeStrengthService = Depends(get_relative_strength_service),
) -> RelativeStrengthAllResponse:
    """全銘柄・全期間のレラティブストレングスを計算・保存します（初期投入 or 再計算用）."""
    try:
        result = await service.calculate_all()

        status_str = "partial_error" if result.error_count > 0 else "completed"

        return RelativeStrengthAllResponse(
            status=status_str,
            total_symbols=result.total_symbols,
            total_rowcount=result.total_rowcount,
            error_count=result.error_count,
            message=result.message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


__all__ = ["router"]
