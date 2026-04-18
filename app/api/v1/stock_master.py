"""銘柄マスタAPI.

銘柄マスタの取得・更新を行うエンドポイント群を提供します。
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi import status as http_status
from pydantic import BaseModel

from app.api.dependencies.services import get_stock_master_service
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.services.data_synchronization.market_data.stock_master import StockMasterService

router = APIRouter(tags=["stock-master"])


class FetchResponse(BaseModel):
    """銘柄マスタ取得レスポンス.

    Attributes:
        message (str): 結果メッセージ
        updated_count (int): 更新件数
        nikkei225 (Optional[Dict]): 日経225更新結果
    """

    message: str
    updated_count: int
    nikkei225: Optional[Dict[str, Any]] = None


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
    "/fetch",
    response_model=FetchResponse,
    status_code=http_status.HTTP_200_OK,
)
async def fetch_stock_master(
    service: StockMasterService = Depends(get_stock_master_service),
) -> FetchResponse:
    """銘柄マスタを取得して保存します.

    JPXから最新の銘柄情報を取得してDBに保存します。
    併せて以下の関連マスターテーブルも作成/更新されます:
    - 市場区分、業種(17/33)、規模などのマスターデータ
    - 銘柄コードマッピング

        **関連テーブル:**
        - 書込/UPSERT:
            - `stock_master`
            - `stock_master_updates`
            - `market_category_master`
            - `sector_33_master`
            - `sector_17_master`
            - `scale_master`
            - `stock_code_mapping`

    Args:
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        FetchResponse: 更新結果
    """
    try:
        result = await service.fetch_and_save()
        return FetchResponse(
            message="Stock master fetch completed",
            updated_count=result["stock_master"]["updated_count"],
            nikkei225=result["nikkei225"],
        )
    except Exception as e:
        raise ServiceError(
            message=f"Failed to fetch stock master: {str(e)}",
        ) from e


@router.post(
    "/fetch/sample",
    response_model=FetchResponse,
    status_code=http_status.HTTP_200_OK,
)
async def fetch_stock_master_sample(
    sample_size: int = Query(100, gt=0, le=5000, description="Number of symbols to store"),
    batch_size: int = Query(500, gt=0, le=5000, description="Batch size"),
    service: StockMasterService = Depends(get_stock_master_service),
) -> FetchResponse:
    """銘柄マスタの先頭N件のみを取得してDBに保持する (テスト用).

    fetch エンドポイントと同じ処理ですが、保存対象件数を制限します。

        **関連テーブル:**
        - 書込/UPSERT:
            - `stock_master`
            - `stock_master_updates`
            - `market_category_master`
            - `sector_33_master`
            - `sector_17_master`
            - `scale_master`
            - `stock_code_mapping`

    Args:
        sample_size (int): 保存する銘柄件数（デフォルト: 100）
        batch_size (int): バッチ処理のサイズ（デフォルト: 500）
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        FetchResponse: 更新結果
    """
    try:
        result = await service.fetch_and_save(limit=sample_size, batch_size=batch_size)
        return FetchResponse(
            message=(f"Stock master sample fetch completed " f"(sample_size={sample_size})"),
            updated_count=result["stock_master"]["updated_count"],
            nikkei225=result["nikkei225"],
        )
    except Exception as e:
        raise ServiceError(
            message=f"Failed to fetch stock master sample: {str(e)}",
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

    **関連テーブル:**
    - 読取: `stock_master`

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

    **関連テーブル:**
    - 読取: `stock_master`, `market_category_master`

    Args:
        market (str): 市場名（例: "プライム", "スタンダード", "グロース"）
        service (StockMasterService): 銘柄マスタサービス

    Returns:
        SymbolListResponse: 銘柄コードリスト
    """
    try:
        symbols = await service.get_symbols_by_market(market)
        if not symbols:
            raise RecordNotFoundError(message=f"No symbols found for market '{market}'")
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

    **関連テーブル:**
    - 削除: `stock_master`

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
