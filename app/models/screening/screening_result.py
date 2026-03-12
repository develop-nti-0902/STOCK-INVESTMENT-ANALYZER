"""スクリーニング結果を保持する ORM モデル."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Date, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class ScreeningResult(SerialPKMixin, TimestampMixin, Base):
    """高配当スクリーニング結果のメタ情報を保持するモデル."""

    __tablename__ = "screening_results"

    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    evaluation_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_year_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    pass_required_conditions: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    total_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_dividend: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_eps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_stability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_profitability: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_eligible", server_default=text("'not_eligible'")
    )
    failed_conditions: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    screening_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "evaluation_year", name="uq_screening_results_symbol_year"),
        Index("idx_screening_results_symbol", "symbol"),
        Index("idx_screening_results_evaluation_year", "evaluation_year"),
        Index("idx_screening_results_status", "status"),
        Index("idx_screening_results_total_score", "total_score"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """短いデバッグ用表示を返します."""
        return (
            "<ScreeningResult(symbol="
            f"{self.symbol!r}, evaluation_year={self.evaluation_year!r}, status={self.status!r})>"
        )

    @property
    def pass_required(self) -> bool:  # pragma: no cover - trivial
        """旧来の `pass_required` 呼び出しとの互換性を維持します."""
        return self.pass_required_conditions


__all__ = ["ScreeningResult"]
