"""EDINET 配当メトリクス用 Pydantic スキーマ."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EdinetDividendMetricsCreate(BaseModel):
    """配当メトリクス作成スキーマ."""

    model_config = ConfigDict(from_attributes=True)

    edinet_document_id: int = Field(..., description="EDINET ドキュメント ID")
    period_end_date: date = Field(..., description="決算期末日")
    fiscal_year: Optional[int] = Field(None, description="会計年度")
    dividend_actual: Optional[Decimal] = Field(None, description="実績配当（円）")
    eps: Optional[Decimal] = Field(None, description="1株当たり利益（円）")
    payout_ratio: Optional[Decimal] = Field(None, description="配当性向")
    is_consolidated: Optional[bool] = Field(None, description="連結フラグ")


class EdinetDividendMetricsRead(EdinetDividendMetricsCreate):
    """配当メトリクス読込スキーマ."""

    id: int = Field(..., description="ID")
    created_at: datetime = Field(..., description="作成日時")
    updated_at: datetime = Field(..., description="更新日時")


__all__ = [
    "EdinetDividendMetricsCreate",
    "EdinetDividendMetricsRead",
]
