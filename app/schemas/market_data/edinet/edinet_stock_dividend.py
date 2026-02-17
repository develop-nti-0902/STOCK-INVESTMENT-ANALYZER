"""EDINET 配当情報用 Pydantic スキーマ.

移動元: app/schemas/edinet_stock_dividend.py
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.core.base import BaseRequestSchema, BaseResponseSchema


class EdinetStockDividendBase(BaseModel):
    """EDINET 配当情報の共通スキーマ定義."""

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra="forbid",
    )

    doc_id: str = Field(..., description="EDINET ドキュメントID", max_length=50)
    sec_code: str = Field(..., description="証券コード／コード系", max_length=10)
    submission_date: date = Field(..., description="提出日")
    period_end_date: date = Field(..., description="決算期末日")
    fiscal_year: Optional[int] = Field(None, description="会計年度")
    report_type: str = Field(..., description="報告種別", max_length=20)

    dividend_actual: Optional[Decimal] = Field(None, description="年間配当金")

    candidate_contexts: Optional[str] = Field(None, description="候補コンテキスト", max_length=50)
    candidate_keys: Optional[str] = Field(None, description="候補キー", max_length=50)
    is_consolidated: Optional[bool] = Field(None, description="連結フラグ")

    @field_validator("doc_id", "sec_code", mode="before")
    @classmethod
    def _strip_strings(cls, v: str) -> str:
        if v is None:
            return v
        return v.strip()

    @field_validator("dividend_actual", mode="before")
    @classmethod
    def _to_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except Exception as exc:
            raise ValueError("数値フィールドは Decimal に変換可能である必要があります") from exc


class EdinetStockDividendCreate(BaseRequestSchema, EdinetStockDividendBase):
    """作成用スキーマ（入力バリデーション）."""


class EdinetStockDividendRead(BaseResponseSchema, EdinetStockDividendBase):
    """レスポンス用スキーマ（id/created_at/updated_at を含む）."""


class EdinetStockDividendLatest(BaseModel):
    """最新データ検索用の軽量スキーマ."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid", from_attributes=True)

    sec_code: str = Field(..., description="証券コード", max_length=10)
    period_end_date: date = Field(..., description="決算期末日")
    dividend_actual: Optional[Decimal] = Field(None, description="年間配当金")


__all__ = [
    "EdinetStockDividendBase",
    "EdinetStockDividendCreate",
    "EdinetStockDividendRead",
    "EdinetStockDividendLatest",
]
