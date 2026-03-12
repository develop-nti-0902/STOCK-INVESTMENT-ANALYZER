"""株価データAPI.

データベースに格納されている株価データを取得するエンドポイント群を提供します。
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import get_stock_price_service
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.exceptions.validation import FieldValidationError
from app.services.data_synchronization.market_data.stock_price.service import StockPriceService
from app.utils.database import get_db

router = APIRouter(tags=["stock-price"])


class StockPriceData(BaseModel):
    """株価データレスポンス.

    Attributes:
        symbol (str): 銘柄コード
        timestamp (Optional[datetime]): タイムスタンプ
        open (float): 始値
        high (float): 高値
        low (float): 安値
        close (float): 終値
        adj_close (Optional[float]): 調整終値
        volume (int): 出来高
    """

    symbol: str
    timestamp: Optional[datetime] = None
    open: float
    high: float
    low: float
    close: float
    adj_close: Optional[float] = None
    volume: int


class StockPriceListResponse(BaseModel):
    """株価データ一覧レスポンス.

    Attributes:
        symbol (str): 銘柄コード
        timeframe (str): 時間軸
        data (List[StockPriceData]): データ一覧
        count (int): 件数
    """

    symbol: str
    timeframe: str
    data: List[StockPriceData]
    count: int


class DeleteAllResponse(BaseModel):
    """全データ削除レスポンス.

    Attributes:
        message (str): 結果メッセージ
        timeframe (str): 対象時間軸
        deleted_count (int): 削除件数
    """

    message: str
    timeframe: str
    deleted_count: int


class FetchRequest(BaseModel):
    """フェッチ＆保存リクエスト."""

    symbols: List[str]
    timeframe: str = Field(
        ...,
        description="Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)",
        pattern="^(1m|5m|15m|30m|1h|1d|1wk|1mo)$",
    )
    period: Optional[str] = None


class FetchResultItem(BaseModel):
    """個別フェッチ結果アイテム."""

    symbol: str
    timeframe: str
    success: bool
    records_processed: int
    records_saved: int
    errors: List[str] = []
    warnings: List[str] = []


class FetchResponse(BaseModel):
    """フェッチ結果一覧レスポンス."""

    results: List[FetchResultItem]


class BatchRequest(BaseModel):
    """JPX全銘柄一括取得リクエスト."""

    timeframe: str = Field(
        ...,
        description="Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)",
        pattern="^(1m|5m|15m|30m|1h|1d|1wk|1mo)$",
    )
    market: Optional[str] = None
    batch_size: int = 100
    period: Optional[str] = None


class BatchResponse(BaseModel):
    """バッチ実行サマリレスポンス."""

    total: int
    success: int
    failed: int
    errors: List[dict]
    elapsed_time: float


@router.get(
    "/{symbol}/{timeframe}",
    response_model=StockPriceListResponse,
    status_code=http_status.HTTP_200_OK,
)
async def get_stock_price_data(
    symbol: str = Path(..., description="Stock symbol (e.g., 7203)"),
    timeframe: str = Path(
        ...,
        description="Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)",
        pattern="^(1m|5m|15m|30m|1h|1d|1wk|1mo)$",
    ),
    start: Optional[str] = Query(
        None,
        description=("Start datetime (ISO format: YYYY-MM-DD or " "YYYY-MM-DDTHH:MM:SS)"),
    ),
    end: Optional[str] = Query(
        None,
        description=("End datetime (ISO format: YYYY-MM-DD or " "YYYY-MM-DDTHH:MM:SS)"),
    ),
    limit: int = Query(
        1000,
        gt=0,
        le=10000,
        description="Maximum number of records to retrieve",
    ),
    offset: int = Query(0, ge=0, description="Offset"),
    service: StockPriceService = Depends(get_stock_price_service),
    db: AsyncSession = Depends(get_db),
):
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # pylint: disable=too-many-locals,too-many-branches
    """指定銘柄・時間軸の株価データを取得.

    データベースに格納されている株価データを返します。

        **関連テーブル:**
        - 読取:
            - `stocks_1m`
            - `stocks_5m`
            - `stocks_15m`
            - `stocks_30m`
            - `stocks_1h`
            - `stocks_1d`
            - `stocks_1wk`
            - `stocks_1mo` (時間軸に応じたテーブル)

    Args:
        symbol (str): 銘柄コード
        timeframe (str): 時間軸
        start (Optional[str]): 開始日時（ISO形式、オプション）
        end (Optional[str]): 終了日時（ISO形式、オプション）
        limit (int): 取得件数上限（デフォルト: 1000）
        offset (int): オフセット（デフォルト: 0）
        db (AsyncSession): DBセッション

    Returns:
        StockPriceListResponse: 株価データリスト
    """
    # 日時パラメータのパース
    start_dt: Optional[datetime] = None
    end_dt: Optional[datetime] = None

    if start:
        try:
            start_dt = datetime.fromisoformat(start)
        except ValueError:
            try:
                start_dt = datetime.fromisoformat(f"{start}T00:00:00")
            except ValueError:
                raise FieldValidationError(
                    message=f"Invalid start date format: {start}",
                ) from None

    if end:
        try:
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            try:
                end_dt = datetime.fromisoformat(f"{end}T23:59:59")
            except ValueError:
                raise FieldValidationError(
                    message=f"Invalid end date format: {end}",
                ) from None

    try:
        rows = await service.get_stock_data_from_db(
            db=db,
            symbol=symbol,
            timeframe=timeframe,
            start=start_dt,
            end=end_dt,
            limit=limit,
            offset=offset,
        )

        data_list = [StockPriceData(**r) for r in rows]

        return StockPriceListResponse(
            symbol=symbol,
            timeframe=timeframe,
            data=data_list,
            count=len(data_list),
        )
    except (FieldValidationError, RecordNotFoundError):
        raise
    except Exception as e:
        raise ServiceError(
            message=f"Failed to fetch data: {str(e)}",
        ) from e


@router.post(
    "/fetch",
    response_model=FetchResponse,
    status_code=http_status.HTTP_200_OK,
)
async def fetch_and_save_stock_price(
    req: FetchRequest,
    service: StockPriceService = Depends(get_stock_price_service),
):
    """指定銘柄リストの株価データを取得して保存する (fetch_and_save を呼ぶ).

    Yahoo Finance から最新データを取得し、指定時間軸のテーブルに保存します。

        **関連テーブル:**
        - 書込:
            - `stocks_1m`
            - `stocks_5m`
            - `stocks_15m`
            - `stocks_30m`
            - `stocks_1h`
            - `stocks_1d`
            - `stocks_1wk`
            - `stocks_1mo` (時間軸に応じたテーブル)
    """
    try:
        results = await service.fetch_and_save(
            symbols=req.symbols, timeframe=req.timeframe, period=req.period
        )

        items = [
            FetchResultItem(
                symbol=r.symbol,
                timeframe=r.timeframe,
                success=r.success,
                records_processed=r.records_processed,
                records_saved=r.records_saved,
                errors=r.errors or [],
                warnings=r.warnings or [],
            )
            for r in results
        ]

        return FetchResponse(results=items)

    except Exception as e:
        raise ServiceError(message=f"Failed to fetch and save data: {str(e)}") from e


@router.post(
    "/batch",
    response_model=BatchResponse,
    status_code=http_status.HTTP_200_OK,
)
async def execute_jpx_batch(
    req: BatchRequest,
    service: StockPriceService = Depends(get_stock_price_service),
):
    """JPX 全銘柄を対象に指定時間軸で一括取得・保存を実行します.

    stock_master から全銘柄を取得し、各銘柄の株価データを示指時間軸で一括保存します。

        **関連テーブル:**
        - 読取:
            - `stock_master`
        - 書込:
            - `stocks_1m`
            - `stocks_5m`
            - `stocks_15m`
            - `stocks_30m`
            - `stocks_1h`
            - `stocks_1d`
            - `stocks_1wk`
            - `stocks_1mo` (時間軸に応じたテーブル)
    """
    try:
        summary = await service.fetch_and_save_for_all_jpx(
            timeframe=req.timeframe, market=req.market, batch_size=req.batch_size, period=req.period
        )

        # 明示的に型を合わせて返す
        return BatchResponse(
            total=int(summary.get("total", 0)),
            success=int(summary.get("success", 0)),
            failed=int(summary.get("failed", 0)),
            errors=summary.get("errors", []),
            elapsed_time=float(summary.get("elapsed_time", 0.0)),
        )
    except Exception as e:
        raise ServiceError(message=f"Failed to execute JPX batch: {str(e)}") from e


@router.delete(
    "/{timeframe}/all",
    response_model=DeleteAllResponse,
    status_code=http_status.HTTP_200_OK,
)
async def delete_all_stock_price_data(
    timeframe: str = Path(
        ...,
        description="Timeframe (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)",
        pattern="^(1m|5m|15m|30m|1h|1d|1wk|1mo)$",
    ),
    service: StockPriceService = Depends(get_stock_price_service),
    db: AsyncSession = Depends(get_db),
):
    """指定時間軸の全株価データを削除.

    指定された時間軸テーブルの全レコードを削除します。取り消し不可です。

        **関連テーブル:**
        - 削除:
            - `stocks_1m`
            - `stocks_5m`
            - `stocks_15m`
            - `stocks_30m`
            - `stocks_1h`
            - `stocks_1d`
            - `stocks_1wk`
            - `stocks_1mo` (時間軸に応じたテーブル)

    Args:
        timeframe (str): 時間軸
        db (AsyncSession): DBセッション

    Returns:
        DeleteAllResponse: 削除結果
    """
    try:
        deleted_count = await service.delete_all_for_timeframe(db=db, timeframe=timeframe)

        return DeleteAllResponse(
            message=f"Successfully deleted all data for {timeframe}",
            timeframe=timeframe,
            deleted_count=deleted_count,
        )
    except FieldValidationError:
        raise
    except Exception as e:
        raise ServiceError(
            message=f"Failed to delete data: {str(e)}",
        ) from e
