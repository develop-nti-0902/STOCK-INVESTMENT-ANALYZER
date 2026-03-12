"""配当利回り履歴 Pydantic スキーマ."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GenerateDividendYieldHistoryRequest(BaseModel):
    """配当利回り履歴生成リクエスト."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    target_date: date = Field(
        ...,
        description="計算対象日（YYYY-MM-DD）。未来日は許可されない。",
    )


class GenerateDividendYieldHistoryResponse(BaseModel):
    """配当利回り履歴生成レスポンス."""

    model_config = ConfigDict(validate_assignment=True, extra="allow")

    status: str = Field(
        ...,
        description="処理ステータス（'completed' | 'partial_error' | 'no_data'）",
    )
    rowcount: int = Field(
        ...,
        description="生成・UPSERT件数",
    )
    skipped_count: int = Field(
        ...,
        description="スキップ件数（データ不足など）",
    )
    error_count: int = Field(
        ...,
        description="エラー件数",
    )
    message: Optional[str] = Field(
        None,
        description="詳細メッセージ",
    )


__all__ = [
    "GenerateDividendYieldHistoryRequest",
    "GenerateDividendYieldHistoryResponse",
]
