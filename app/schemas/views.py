"""ビュー関連のスキーマ定義."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LatestStockBase(BaseModel):
    """latest_stocks_1dビューの基本スキーマ."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str = Field(..., description="銘柄コード")
    timestamp: datetime = Field(..., description="タイムスタンプ（UTC）")
    open: Decimal = Field(..., description="始値")
    high: Decimal = Field(..., description="高値")
    low: Decimal = Field(..., description="安値")
    close: Decimal = Field(..., description="終値")
    adj_close: Decimal | None = Field(None, description="調整終値")
    volume: int = Field(..., description="出来高")


class LatestStockResponse(LatestStockBase):
    """latest_stocks_1dビューのレスポンススキーマ."""

    id: int = Field(..., description="レコードID")


__all__ = ["LatestStockBase", "LatestStockResponse"]
