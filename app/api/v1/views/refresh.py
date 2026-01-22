from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.services import get_latest_stocks_refresh_service
from app.exceptions.business import ServiceError
from app.services.views.refresh_service import LatestStocksRefreshService

router = APIRouter(tags=["views"])  # OpenAPI tag: views


@router.post(
    "/refresh-latest-stocks",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Refresh latest_stocks_1d materialized view",
)
async def refresh_latest_stocks(
    service: LatestStocksRefreshService = Depends(
        get_latest_stocks_refresh_service
    ),
):
    """Enqueue a refresh job for the `latest_stocks_1d` materialized view.

    呼び出すとジョブを登録し、ジョブIDを返却する。
    """
    try:
        job_id = await service.enqueue_refresh()
        return {"job_id": job_id}
    except ServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


__all__ = ["router"]
