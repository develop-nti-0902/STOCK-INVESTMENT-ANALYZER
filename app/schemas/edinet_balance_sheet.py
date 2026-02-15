"""EDINET 貸借対照表用 Pydantic スキーマ.

このモジュールは GitHub Issue #283 の実装対象で、
`app/models/edinet_balance_sheet.py` のモデルに対応する
リクエスト／レスポンス用の Pydantic スキーマを提供します。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.core.base import BaseRequestSchema, BaseResponseSchema


class EdinetBalanceSheetBase(BaseModel):
    """EDINET 貸借対照表の共通スキーマ定義."""

    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        extra="forbid",
    )

    doc_id: str = Field(..., description="EDINET ドキュメントID", max_length=50)
    sec_code: str = Field(..., description="証券コード／コード系", max_length=10)
    filer_name: Optional[str] = Field(None, description="提出者名", max_length=255)
    submission_date: date = Field(..., description="提出日")
    period_end_date: date = Field(..., description="決算期末日")
    fiscal_year: Optional[int] = Field(None, description="会計年度")
    report_type: str = Field(..., description="報告種別", max_length=20)

    # 主要数値（Decimal を使って精度を保つ）
    total_assets: Optional[Decimal] = Field(None, description="総資産")
    current_assets: Optional[Decimal] = Field(None, description="流動資産")
    non_current_assets: Optional[Decimal] = Field(None, description="固定資産")
    cash_and_equivalents: Optional[Decimal] = Field(None, description="現金及び現金同等物")

    total_liabilities: Optional[Decimal] = Field(None, description="総負債")
    current_liabilities: Optional[Decimal] = Field(None, description="流動負債")
    non_current_liabilities: Optional[Decimal] = Field(None, description="固定負債")

    total_equity: Optional[Decimal] = Field(None, description="純資産（総資本）")
    shareholders_equity: Optional[Decimal] = Field(None, description="株主資本")
    retained_earnings: Optional[Decimal] = Field(None, description="利益剰余金")

    candidate_contexts: Optional[str] = Field(None, description="候補コンテキスト", max_length=50)
    candidate_keys: Optional[str] = Field(None, description="候補キー", max_length=50)
    is_consolidated: Optional[bool] = Field(None, description="連結フラグ")

    @field_validator("doc_id", "sec_code", "filer_name", mode="before")
    @classmethod
    def _strip_strings(cls, v: str) -> str:
        if v is None:
            return v
        return v.strip()

    @field_validator(
        "total_assets",
        "current_assets",
        "non_current_assets",
        "cash_and_equivalents",
        "total_liabilities",
        "current_liabilities",
        "non_current_liabilities",
        "total_equity",
        "shareholders_equity",
        "retained_earnings",
        mode="before",
    )
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


class EdinetBalanceSheetCreate(BaseRequestSchema, EdinetBalanceSheetBase):
    """作成用スキーマ（入力バリデーション）."""


class EdinetBalanceSheetRead(BaseResponseSchema, EdinetBalanceSheetBase):
    """レスポンス用スキーマ（id/created_at/updated_at を含む）."""


class EdinetBalanceSheetLatest(BaseModel):
    """最新データ検索用の軽量スキーマ."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid", from_attributes=True)

    sec_code: str = Field(..., description="証券コード", max_length=10)
    period_end_date: date = Field(..., description="決算期末日")
    total_assets: Optional[Decimal] = Field(None, description="総資産")
    total_equity: Optional[Decimal] = Field(None, description="純資産")


__all__ = [
    "EdinetBalanceSheetBase",
    "EdinetBalanceSheetCreate",
    "EdinetBalanceSheetRead",
    "EdinetBalanceSheetLatest",
]
