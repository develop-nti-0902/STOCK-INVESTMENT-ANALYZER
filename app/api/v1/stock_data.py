from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies.services import get_stock_price_service
from app.schemas.stock_data import StockPriceResponse
from app.services.market_data.stock_price.service import StockPriceService

router = APIRouter()


class StockDataListResponse(BaseModel):
    """銘柄の株価データ一覧レスポンスモデル

    - `symbol`: 銘柄コード
    - `data`: `StockPriceResponse` のリスト
    - `count`: 返却件数
    """

    symbol: str
    data: List[StockPriceResponse]
    count: int


@router.get("/{symbol}", response_model=StockDataListResponse)
async def get_stock_data(
    symbol: str,
    timeframe: str = Query("1d", description="Timeframe (e.g. 1d, 1wk)"),
    start_date: Optional[str] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: Optional[int] = Query(
        None, gt=0, description="Max number of records to return (optional)"
    ),
    service: StockPriceService = Depends(get_stock_price_service),
):
    """単一銘柄の読み取り専用株価データを返すエンドポイント

    - データが存在しない場合はHTTP 404を返します。
    - `limit` 指定で返却件数を制限できます。
    """
    # サービスからデータを取得
    result = await service.get_stock_data(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )

    # データ未取得時は404を返す
    if result is None or result.data is None or result.data.empty:
        raise HTTPException(
            status_code=404, detail="指定した銘柄のデータが見つかりません"
        )

    df = result.data

    # limit が指定されていれば先頭から切り取る
    if limit is not None:
        df = df.head(limit)

    # pandas の型（NaN 等）を None に置換して辞書化
    records = df.where(df.notnull(), None).to_dict(orient="records")

    # 辞書化後に float('nan') 等が残ることがあるので明示的に None に変換
    import pandas as _pd

    for r in records:
        for k, v in list(r.items()):
            try:
                if _pd.isna(v):
                    r[k] = None
            except Exception:
                # isna が使えない型は無視
                pass

        # 日付フィールドがあれば ISO 形式の文字列に変換する
        if "trade_date" in r and r["trade_date"] is not None:
            try:
                r["trade_date"] = r["trade_date"].isoformat()
            except Exception:
                # datetime 型でない場合はそのままにする
                pass

    return {"symbol": symbol, "data": records, "count": len(records)}
