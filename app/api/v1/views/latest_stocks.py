from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.services import (
    get_latest_stocks_refresh_service,
    get_latest_stocks_service,
)
from app.exceptions.business import ServiceError
from app.schemas.views import LatestStockResponse
from app.services.views.latest_stocks_service import LatestStocksService
from app.services.views.refresh_service import LatestStocksRefreshService

router = APIRouter(tags=["views"])  # OpenAPI tag: views


@router.post(
    "/refresh-latest-stocks",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Refresh latest_stocks view",
)
async def refresh_latest_stocks(
    service: LatestStocksRefreshService = Depends(
        get_latest_stocks_refresh_service
    ),
):
    """Enqueue a background refresh job for the
    `latest_stocks_1d` materialized view.

    呼び出すと更新処理を非同期ジョブとして登録します。
    登録したジョブのIDをレスポンスとして返却します。
    実際のリフレッシュはバックグラウンドで行われます。
    処理状況の取得は別途ジョブステータス確認用の仕組みを利用してください
    （HTTP 202 Accepted）。
    """
    try:
        job_id = await service.enqueue_refresh()
        return {"job_id": job_id}
    except ServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/latest-stocks/{symbol}",
    response_model=LatestStockResponse,
    summary="Get latest stock data by symbol",
)
async def get_latest_stock(
    symbol: str,
    service: LatestStocksService = Depends(get_latest_stocks_service),
):
    """Get the latest stock data for a specific symbol.

    Args:
        symbol: 銘柄コード（例: 7203.T）

    Returns:
        最新の株価情報

    Raises:
        404: 銘柄が見つからない場合
        500: サーバーエラー
    """
    try:
        result = await service.get_latest_stock(symbol)
        return result
    except ServiceError as exc:
        if "not found" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


__all__ = ["router"]
