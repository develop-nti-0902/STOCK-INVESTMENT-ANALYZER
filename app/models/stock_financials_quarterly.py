"""四半期損益モデル定義モジュール.

`stock_financials_quarterly` テーブルに対応する SQLAlchemy モデルを定義します。
"""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockFinancialsQuarterly(SerialPKMixin, TimestampMixin, Base):
    """四半期損益（`stock_financials_quarterly`）モデル."""

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=False)

    revenue: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    net_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    basic_eps: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    diluted_eps: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)

    __table_args__ = (
        Index("idx_stock_finq_symbol", "symbol"),
        Index("idx_stock_finq_year_quarter", "fiscal_year", "fiscal_quarter"),
        Index(
            "uq_stock_finq_symbol_year_quarter",
            "symbol",
            "fiscal_year",
            "fiscal_quarter",
            unique=True,
        ),
    )


__all__ = ["StockFinancialsQuarterly"]
