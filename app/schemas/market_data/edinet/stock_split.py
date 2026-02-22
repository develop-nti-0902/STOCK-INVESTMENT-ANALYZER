"""株式分割用 Pydantic スキーマ（stock_split）。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.core.base import BaseRequestSchema, BaseResponseSchema


class StockSplitBase(BaseModel):
    """共通スキーマ定義."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True, extra="forbid")

    code: str = Field(..., description="銘柄コード", max_length=20)
    effective_date: date = Field(..., description="発効日")
    ratio_from: Optional[int] = Field(None, description="分割前比率")
    ratio_to: Optional[int] = Field(None, description="分割後比率")

    @field_validator("code", mode="before")
    @classmethod
    def _strip_code(cls, v: str) -> str:
        if v is None:
            return v
        return v.strip()

    @field_validator("ratio_from", "ratio_to", mode="before")
    @classmethod
    def _to_int(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except Exception as exc:
            raise ValueError("ratio fields must be integer-convertible") from exc


class StockSplitCreate(BaseRequestSchema, StockSplitBase):
    """作成用スキーマ（入力）"""


class StockSplitRead(BaseResponseSchema, StockSplitBase):
    """レスポンス用スキーマ（id/created_at/updated_at 含む）"""


__all__ = ["StockSplitBase", "StockSplitCreate", "StockSplitRead"]
