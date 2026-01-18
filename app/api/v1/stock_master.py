"""銘柄マスタAPI.

銘柄マスタの取得・更新を行うエンドポイント群を提供します。
"""

from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from pydantic import BaseModel

from app.api.dependencies.services import get_stock_master_service
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.services.market_data.stock_master.service import StockMasterService

router = APIRouter(tags=["stock-master"])


class RefreshResponse(BaseModel):
    """銘柄マスタ更新レスポンス.

    Attributes:
        message (str): 結果メッセージ
        updated_count (int): 更新件数
    """

    message: str
    updated_count: int


class SymbolListResponse(BaseModel):
    """銘柄コードリストレスポンス.

    Attributes:
        symbols (List[str]): 銘柄コード一覧
        count (int): 件数
    """

    symbols: List[str]
    count: int


class ResetResponse(BaseModel):
    """銘柄マスタリセットレスポンス.

    Attributes:
        message (str): 結果メッセージ
        deleted_count (int): 削除件数
    """

    message: str
    deleted_count: int


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    status_code=http_status.HTTP_200_OK,
)
async def refresh_stock_master(
    batch_size: int = Query(500, gt=0, le=5000, description="Batch size"),
    service: StockMasterService = Depends(get_stock_master_service),
) -> RefreshResponse:
    """銘柄マスタを最新情報で更新.

    JPXから最新の銘柄情報を取得してDBに保存します。

    Args:
        batch_size (int): バッチ処理のサイズ（デフォルト: 500）
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        RefreshResponse: 更新結果
    """
    try:
        updated_count = await service.fetch_and_store(batch_size=batch_size)
        return RefreshResponse(
            message="Stock master refresh completed",
            updated_count=updated_count,
        )
    except Exception as e:
        raise ServiceError(
            message=f"Failed to refresh stock master: {str(e)}",
        ) from e


@router.get(
    "/symbols",
    response_model=SymbolListResponse,
    status_code=http_status.HTTP_200_OK,
)
async def get_all_active_symbols(
    service: StockMasterService = Depends(get_stock_master_service),
) -> SymbolListResponse:
    """アクティブな全銘柄コードを取得.

    Args:
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        SymbolListResponse: 銘柄コードリスト
    """
    try:
        symbols = await service.get_all_active_symbols()
        return SymbolListResponse(symbols=symbols, count=len(symbols))
    except Exception as e:
        raise ServiceError(
            message=f"Failed to retrieve stock symbols: {str(e)}",
        ) from e


@router.get(
    "/symbols/market/{market}",
    response_model=SymbolListResponse,
    status_code=http_status.HTTP_200_OK,
)
async def get_symbols_by_market(
    market: str,
    service: StockMasterService = Depends(get_stock_master_service),
) -> SymbolListResponse:
    """市場別の銘柄コードを取得.

    Args:
        market (str): 市場名（例: "プライム", "スタンダード", "グロース"）
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        SymbolListResponse: 銘柄コードリスト
    """
    try:
        symbols = await service.get_symbols_by_market(market)
        if not symbols:
            raise RecordNotFoundError(
                message=f"No symbols found for market '{market}'"
            )
        return SymbolListResponse(symbols=symbols, count=len(symbols))
    except RecordNotFoundError:
        raise
    except Exception as e:
        raise ServiceError(
            message=f"Failed to retrieve stock symbols: {str(e)}",
        ) from e


@router.delete(
    "/reset",
    response_model=ResetResponse,
    status_code=http_status.HTTP_200_OK,
)
async def reset_stock_master(
    service: StockMasterService = Depends(get_stock_master_service),
) -> ResetResponse:
    """銘柄マスタの全データを削除.

    ⚠️ 警告: このエンドポイントは全ての銘柄マスタデータを削除します。

    Args:
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        ResetResponse: 削除結果
    """
    try:
        deleted_count = await service.reset_stock_master()
        return ResetResponse(
            message="Stock master reset completed",
            deleted_count=deleted_count,
        )
    except Exception as e:
        raise ServiceError(
            message=f"Failed to reset stock master: {str(e)}",
        ) from e
