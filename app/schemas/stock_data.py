"""株価データ Pydantic スキーマ.

株価データの作成／レスポンス／バッチ処理用スキーマを定義します。
仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StockPriceBase(BaseModel):
    """株価データ基底スキーマ.

    共通フィールドを提供します（symbol, timestamp, open_price, high,
    low, close, volume, adj_close）。
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
    timestamp: datetime = Field(
        description="取引日時（タイムスタンプ、JST）", alias="trade_date"
    )
    open_price: Optional[float] = Field(None, description="始値")
    high: Optional[float] = Field(None, description="高値")
    low: Optional[float] = Field(None, description="安値")
    close: Optional[float] = Field(None, description="終値")
    volume: Optional[int] = Field(None, description="出来高")
    adj_close: Optional[float] = Field(None, description="調整後終値")


class StockPriceCreate(StockPriceBase):
    """株価データ作成スキーマ.

    データベース挿入時に使用するバリデーションを行います。
    """

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """銘柄コードのバリデーション.

        Args:
            v (str): 入力される銘柄コード

        Returns:
            str: 正規化された銘柄コード
        """
        if not v or not v.strip():
            raise ValueError("銘柄コードは必須です")
        return v.strip().upper()


class StockPriceResponse(StockPriceBase):
    """株価データレスポンススキーマ.

    API レスポンス用に `id`, `created_at`, `updated_at` を追加します。
    """

    id: Optional[int] = Field(None, description="レコードID")
    created_at: Optional[datetime] = Field(None, description="作成日時")
    updated_at: Optional[datetime] = Field(None, description="更新日時")


class StockPriceBatch(BaseModel):
    """株価データバッチ処理スキーマ.

    複数銘柄の株価データをまとめて処理する際に使用します。
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",
        populate_by_name=True,
    )

    symbol: str = Field(description="銘柄コード")
    timeframe: str = Field(
        description="時間軸（1m, 5m, 15m, 1h, 1d, 1wk, 1mo）"
    )
    data: List[StockPriceCreate] = Field(description="株価データリスト")

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        """時間軸のバリデーション.

        Args:
            v (str): 入力される時間軸文字列

        Returns:
            str: 検証済みの時間軸文字列
        """
        valid_timeframes = ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"]
        if v not in valid_timeframes:
            raise ValueError(f"無効な時間軸です。有効な値: {valid_timeframes}")
        return v


# タイムフレーム別スキーマ（必要に応じて拡張可能）
class StockPrice1M(StockPriceBase):
    """1分足株価データスキーマ."""


class StockPrice5M(StockPriceBase):
    """5分足株価データスキーマ."""


class StockPrice15M(StockPriceBase):
    """15分足株価データスキーマ."""


class StockPrice1H(StockPriceBase):
    """1時間足株価データスキーマ."""


class StockPrice1D(StockPriceBase):
    """日次株価データスキーマ."""


class StockPrice1WK(StockPriceBase):
    """週次株価データスキーマ."""


class StockPrice1MO(StockPriceBase):
    """月次株価データスキーマ."""
