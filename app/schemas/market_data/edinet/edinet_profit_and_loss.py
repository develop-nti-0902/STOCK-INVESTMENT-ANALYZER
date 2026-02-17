"""EDINET 損益用 Pydantic スキーマ.

移動元: app/schemas/edinet_profit_and_loss.py
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.core.base import BaseRequestSchema, BaseResponseSchema


class EdinetProfitAndLossBase(BaseModel):
    """共通フィールド（リクエスト/レスポンス双方で利用するベース）."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True, extra="forbid")

    doc_id: str = Field(..., description="EDINET 文書 ID", max_length=50)
    sec_code: str = Field(..., description="証券コード", max_length=10)
    submission_date: date = Field(..., description="提出日")
    period_end_date: date = Field(..., description="決算期末日")
    fiscal_year: Optional[int] = Field(None, description="会計年度")
    report_type: str = Field("annual", description="報告種別", max_length=20)

    net_sales: Optional[Decimal] = Field(None, description="売上高")
    operating_income: Optional[Decimal] = Field(None, description="営業利益")
    eps: Optional[Decimal] = Field(None, description="1株当たり当期純利益（円）")

    candidate_contexts: Optional[str] = Field(
        None, description="解析で使用された context", max_length=50
    )
    candidate_keys: Optional[str] = Field(None, description="解析で使用された key", max_length=50)
    is_consolidated: Optional[bool] = Field(None, description="連結フラグ")

    @field_validator("doc_id", "sec_code", "candidate_contexts", "candidate_keys", mode="before")
    @classmethod
    def _strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return v.strip()

    @field_validator("net_sales", "operating_income", "eps", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except Exception as exc:  # pragma: no cover - validation error path
            raise ValueError(
                "数値フィールドは数値または Decimal に変換可能である必要があります"
            ) from exc


class EdinetProfitAndLossCreate(BaseRequestSchema, EdinetProfitAndLossBase):
    """作成（リクエスト）用スキーマ."""


class EdinetProfitAndLossRead(BaseResponseSchema, EdinetProfitAndLossBase):
    """レスポンス用スキーマ（`id`, `created_at`, `updated_at` を含む）."""


class EdinetProfitAndLossLatest(BaseModel):
    """軽量レスポンス: 最新データ取得時に使用するスキーマ."""

    model_config = ConfigDict(from_attributes=True, validate_assignment=True, extra="forbid")

    sec_code: str = Field(..., description="証券コード", max_length=10)
    period_end_date: date = Field(..., description="決算期末日")
    net_sales: Optional[Decimal] = Field(None, description="売上高")
    operating_income: Optional[Decimal] = Field(None, description="営業利益")
    eps: Optional[Decimal] = Field(None, description="1株当たり当期純利益（円）")


__all__ = [
    "EdinetProfitAndLossBase",
    "EdinetProfitAndLossCreate",
    "EdinetProfitAndLossRead",
    "EdinetProfitAndLossLatest",
]
