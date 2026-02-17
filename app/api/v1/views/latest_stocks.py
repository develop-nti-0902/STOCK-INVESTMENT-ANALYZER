"""Views: 最新株価取得API. latest_stocks ビューの取得と更新を提供します."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.services import (
    get_latest_stocks_refresh_service,
    get_latest_stocks_service,
)
from app.exceptions.business import ServiceError
from app.schemas.views import LatestStockResponse
from app.services.views.latest_stocks.refresh import LatestStocksRefreshService
from app.services.views.latest_stocks.service import LatestStocksService

router = APIRouter(tags=["views"])  # OpenAPI tag: views


@router.post(
    "/refresh-latest-stocks",
    status_code=status.HTTP_200_OK,
    summary="Refresh latest_stocks view (synchronous)",
)
async def refresh_latest_stocks(
    service: LatestStocksRefreshService = Depends(get_latest_stocks_refresh_service),
):
    """Synchronously refresh the `latest_stocks_1d` view.

    バックグラウンドのジョブ管理を廃止し、呼び出し元で同期的にリフレッシュ処理を実行します。
    成功時は HTTP 200 を返します。
    """
    try:
        await service.run_refresh()
        return {"status": "completed"}
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
