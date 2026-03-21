"""レラティブストレングスデータモデル."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class RelativeStrength(SerialPKMixin, TimestampMixin, Base):
    """レラティブストレングス（RS）データテーブル定義.

    各銘柄の各日付のレラティブストレングス指標を格納.
    William O'Neill式のRS計算に基づく.
    """

    __tablename__ = "relative_strength"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    calculation_date: Mapped[date] = mapped_column(Date, nullable=False)
    change_63days: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    change_126days: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    change_189days: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    change_252days: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    relative_strength_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("symbol", "calculation_date", name="uq_relative_strength_symbol_date"),
        Index("idx_relative_strength_symbol", "symbol"),
        Index("idx_relative_strength_calculation_date", "calculation_date"),
    )

    def __repr__(self) -> str:
        """短いデバッグ用表示を返します."""
        return (
            f"<RelativeStrength(symbol='{self.symbol}', "
            f"date={self.calculation_date.isoformat()}, "
            f"score={self.relative_strength_score})>"
        )


__all__ = ["RelativeStrength"]
