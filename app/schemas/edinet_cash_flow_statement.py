"""EDINET キャッシュフロー用 Pydantic スキーマ.

`app/models/edinet_cash_flow_statement.py` に対応するリクエスト/レスポンス用スキーマを提供します。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.core.base import BaseRequestSchema, BaseResponseSchema


class EdinetCashFlowStatementBase(BaseModel):
    """EDINET キャッシュフローの共通スキーマ定義."""

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

    # 財務指標
    operating_cf: Optional[Decimal] = Field(None, description="営業キャッシュフロー（百万円）")

    # メタデータ項目
    candidate_contexts: Optional[str] = Field(None, description="候補コンテキスト", max_length=50)
    candidate_keys: Optional[str] = Field(None, description="候補キー", max_length=50)
    is_consolidated: Optional[bool] = Field(None, description="連結フラグ")

    @field_validator("doc_id", "sec_code", mode="before")
    @classmethod
    def _strip_strings(cls, v: str) -> str:
        if v is None:
            return v
        return v.strip()

    @field_validator("operating_cf", mode="before")
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


class EdinetCashFlowStatementCreate(BaseRequestSchema, EdinetCashFlowStatementBase):
    """Create schema for input validation."""


class EdinetCashFlowStatementRead(BaseResponseSchema, EdinetCashFlowStatementBase):
    """Response schema including id/created_at/updated_at."""


class EdinetCashFlowStatementLatest(BaseModel):
    """Lightweight schema for latest-data queries."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid", from_attributes=True)

    sec_code: str = Field(..., description="証券コード", max_length=10)
    period_end_date: date = Field(..., description="決算期末日")
    operating_cf: Optional[Decimal] = Field(None, description="営業キャッシュフロー（百万円）")


__all__ = [
    "EdinetCashFlowStatementBase",
    "EdinetCashFlowStatementCreate",
    "EdinetCashFlowStatementRead",
    "EdinetCashFlowStatementLatest",
]
