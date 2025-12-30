"""株価データAPI.

データベースに格納されている株価データを取得するエンドポイント群を提供します。
"""

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stock_data_repository import (
    StockData1dRepository,
    StockData1hRepository,
    StockData1moRepository,
    StockData1mRepository,
    StockData1wkRepository,
    StockData5mRepository,
    StockData15mRepository,
    StockData30mRepository,
)
from app.utils.database import get_db

router = APIRouter(tags=["stock-price"])

# 時間軸とリポジトリのマッピング
TIMEFRAME_REPOSITORY_MAP = {
    "1m": StockData1mRepository,
    "5m": StockData5mRepository,
    "15m": StockData15mRepository,
    "30m": StockData30mRepository,
    "1h": StockData1hRepository,
    "1d": StockData1dRepository,
    "1wk": StockData1wkRepository,
    "1mo": StockData1moRepository,
}


class StockPriceData(BaseModel):
    """株価データレスポンスモデル.

    Attributes:
        symbol (str): 銘柄コード
        timestamp (Optional[datetime]): タイムスタンプ
        trade_date (Optional[date]): 取引日
        open (float): 始値
        high (float): 高値
        low (float): 安値
        close (float): 終値
        adj_close (Optional[float]): 調整終値
        volume (int): 出来高
    """

    symbol: str
    timestamp: Optional[datetime] = None
    trade_date: Optional[date] = None
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
        description=(
            "Start datetime (ISO format: YYYY-MM-DD or " "YYYY-MM-DDTHH:MM:SS)"
        ),
    ),
    end: Optional[str] = Query(
        None,
        description=(
            "End datetime (ISO format: YYYY-MM-DD or " "YYYY-MM-DDTHH:MM:SS)"
        ),
    ),
    limit: int = Query(
        1000,
        gt=0,
        le=10000,
        description="Maximum number of records to retrieve",
    ),
    offset: int = Query(0, ge=0, description="Offset"),
    db: AsyncSession = Depends(get_db),
):
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # pylint: disable=too-many-locals,too-many-branches
    """指定銘柄・時間軸の株価データを取得.

    データベースに格納されている株価データを返します。

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
    # 時間軸に対応するリポジトリを取得
    repo_class = TIMEFRAME_REPOSITORY_MAP.get(timeframe)
    if not repo_class:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timeframe: {timeframe}",
        )

    repo = repo_class(session=db)  # type: ignore[abstract]

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
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start date format: {start}",
                ) from None

    if end:
        try:
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            try:
                end_dt = datetime.fromisoformat(f"{end}T23:59:59")
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid end date format: {end}",
                ) from None

    try:
        # データ取得
        results = await repo.get_by_symbol_and_range(
            symbol=symbol,
            start=start_dt,
            end=end_dt,
            limit=limit,
            offset=offset,
        )

        if not results:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol '{symbol}'",
            )

        # レスポンスデータの構築
        data_list = []
        for row in results:
            data_dict = {
                "symbol": row.symbol,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": row.volume,
            }

            # adj_closeがあれば追加
            if hasattr(row, "adj_close") and row.adj_close is not None:
                data_dict["adj_close"] = float(row.adj_close)

            # timestamp or trade_date
            if hasattr(row, "timestamp"):
                data_dict["timestamp"] = row.timestamp
            if hasattr(row, "trade_date"):
                data_dict["trade_date"] = row.trade_date

            data_list.append(StockPriceData(**data_dict))

        return StockPriceListResponse(
            symbol=symbol,
            timeframe=timeframe,
            data=data_list,
            count=len(data_list),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch data: {str(e)}",
        ) from e


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
    db: AsyncSession = Depends(get_db),
):
    """指定時間軸の全株価データを削除.

    指定された時間軸テーブルの全レコードを削除します。取り消し不可です。

    Args:
        timeframe (str): 時間軸
        db (AsyncSession): DBセッション

    Returns:
        DeleteAllResponse: 削除結果
    """
    # 時間軸に対応するリポジトリを取得
    repo_class = TIMEFRAME_REPOSITORY_MAP.get(timeframe)
    if not repo_class:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timeframe: {timeframe}",
        )

    repo = repo_class(session=db)  # type: ignore[abstract]

    try:
        # 全データ削除
        deleted_count = await repo.delete_all()
        await db.commit()

        return DeleteAllResponse(
            message=f"Successfully deleted all data for {timeframe}",
            timeframe=timeframe,
            deleted_count=deleted_count,
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete data: {str(e)}",
        ) from e
