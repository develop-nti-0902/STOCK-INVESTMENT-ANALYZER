"""株価データスキーマ.

Yahoo Finance API などから取得する株価データを正規化するための Pydantic スキーマを定義します。
仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StockData(BaseModel):
    """株価データモデル.

    Attributes:
        symbol (str): 銘柄コード
        timestamp (datetime): 日時（intraday の場合は時刻を含む）
        open_price (Optional[float]): 始値
        high (Optional[float]): 高値
        low (Optional[float]): 安値
        close (Optional[float]): 終値
        volume (Optional[int]): 出来高
        adj_close (Optional[float]): 調整後終値
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
    # intraday の場合は時刻情報を含むため datetime を受け取る
    timestamp: datetime = Field(description="日時（日次は00:00:00）")
    open_price: Optional[float] = Field(None, description="始値")
    high: Optional[float] = Field(None, description="高値")
    low: Optional[float] = Field(None, description="安値")
    close: Optional[float] = Field(None, description="終値")
    volume: Optional[int] = Field(None, description="出来高")
    adj_close: Optional[float] = Field(None, description="調整後終値")
