"""
株価データスキーマ

Yahoo Finance APIから取得する株価データのPydanticスキーマを定義します。
仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StockData(BaseModel):
    """
    株価データモデル

    Yahoo Finance APIから取得した株価データを正規化した形式です。
    """

    model_config = ConfigDict(
        # フィールドの型チェックを厳密に
        validate_assignment=True,
        # 不明なフィールドを許可（APIレスポンスの変化に対応）
        extra="allow",
        # フィールド名とエイリアスの両方を受け入れる
        populate_by_name=True,
    )

    symbol: str = Field(description="銘柄コード")
    trade_date: date = Field(description="日付")
    open_price: Optional[float] = Field(None, description="始値")
    high: Optional[float] = Field(None, description="高値")
    low: Optional[float] = Field(None, description="安値")
    close: Optional[float] = Field(None, description="終値")
    volume: Optional[int] = Field(None, description="出来高")
    adj_close: Optional[float] = Field(None, description="調整後終値")
