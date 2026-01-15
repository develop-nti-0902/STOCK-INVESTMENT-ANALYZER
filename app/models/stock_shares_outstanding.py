"""発行済株式数（stock_shares_outstanding）モデル定義モジュール.

スナップショットとして発行済株式数や希薄化後株式数を保持します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockSharesOutstanding(SerialPKMixin, TimestampMixin, Base):
    """発行済株式数のスナップショットを格納するモデル."""

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of_date: Mapped[str] = mapped_column(Date, nullable=False)

    shares_outstanding: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 0), nullable=True
    )
    fully_diluted_shares: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 0), nullable=True
    )
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    __table_args__ = (
        Index("idx_stock_shares_symbol", "symbol"),
        Index("idx_stock_shares_date", "as_of_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockSharesOutstanding(symbol="
            + f"{self.symbol!r}, as_of_date={self.as_of_date!r})>"
        )


__all__ = ["StockSharesOutstanding"]
