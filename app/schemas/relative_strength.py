"""レラティブストレングス Pydantic スキーマ."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CalculateRelativeStrengthRequest(BaseModel):
    """指定日付のRS計算リクエスト."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    target_date: date = Field(..., description="計算基準日（YYYY-MM-DD）")


class RelativeStrengthDateResponse(BaseModel):
    """指定日付のRS計算レスポンス."""

    model_config = ConfigDict(validate_assignment=True, extra="allow")
    status: str
    calculation_date: str
    rowcount: int
    skipped_count: int
    error_count: int
    message: Optional[str] = None


class RelativeStrengthAllResponse(BaseModel):
    """全期間RS計算レスポンス."""

    model_config = ConfigDict(validate_assignment=True, extra="allow")
    status: str
    total_symbols: int
    total_rowcount: int
    error_count: int
    message: Optional[str] = None


__all__ = [
    "CalculateRelativeStrengthRequest",
    "RelativeStrengthDateResponse",
    "RelativeStrengthAllResponse",
]
