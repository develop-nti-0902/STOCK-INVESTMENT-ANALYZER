"""日経225データAPI."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi import status as http_status
from pydantic import BaseModel, Field

from app.api.dependencies.services import get_nikkei225_service
from app.exceptions.business import ServiceError
from app.services.data_synchronization.market_data.nikkei225 import Nikkei225Service

router = APIRouter(tags=["nikkei225"])


class FetchRequest(BaseModel):
    """日経225フェッチリクエスト."""

    max_period: Optional[int] = Field(
        None,
        gt=0,
        description="取得する最大日数（省略時は全利用可能データを取得）",
    )


class FetchResponse(BaseModel):
    """日経225フェッチレスポンス."""

    success: bool
    records_fetched: int
    records_saved: int
    errors: List[str] = []
    elapsed_time: float


@router.post(
    "/fetch",
    response_model=FetchResponse,
    status_code=http_status.HTTP_200_OK,
)
async def fetch_nikkei225(
    req: FetchRequest,
    service: Nikkei225Service = Depends(get_nikkei225_service),
) -> FetchResponse:
    """日経225日足データを yfinance から取得してDBに保存する.

    **関連テーブル:**
    - 書込:
        - `nikkei225_1d`
    """
    try:
        result = await service.fetch_and_save(max_period=req.max_period)
        return FetchResponse(
            success=result.success,
            records_fetched=result.records_fetched,
            records_saved=result.records_saved,
            errors=result.errors,
            elapsed_time=result.elapsed_time,
        )
    except Exception as e:
        raise ServiceError(message=f"Nikkei225 fetch failed: {str(e)}") from e
