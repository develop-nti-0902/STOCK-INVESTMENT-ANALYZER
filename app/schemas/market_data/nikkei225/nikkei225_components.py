"""日経225構成銘柄スキーマ."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Nikkei225ComponentCreate(BaseModel):
    """日経225構成銘柄作成スキーマ."""

    stock_code: str = Field(..., min_length=4, max_length=4)
    price_adjustment_factor: Decimal
    effective_date: date


class Nikkei225ComponentRead(Nikkei225ComponentCreate):
    """日経225構成銘柄読み取りスキーマ."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
