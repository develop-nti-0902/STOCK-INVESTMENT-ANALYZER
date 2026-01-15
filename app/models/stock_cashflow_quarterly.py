"""四半期キャッシュフローモデル定義モジュール.

`stock_cashflow_quarterly` テーブルに対応する SQLAlchemy モデルを定義します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockCashflowQuarterly(SerialPKMixin, TimestampMixin, Base):
    """四半期キャッシュフロー（`stock_cashflow_quarterly`）モデル。"""

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=False)

    operating_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    investing_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    financing_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    free_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    capital_expenditure: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    additional_data: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )

    __table_args__ = (
        Index("idx_stock_cashflowq_symbol", "symbol"),
        Index(
            "idx_stock_cashflowq_year_quarter", "fiscal_year", "fiscal_quarter"
        ),
        Index(
            "uq_stock_cashflowq_symbol_year_quarter",
            "symbol",
            "fiscal_year",
            "fiscal_quarter",
            unique=True,
        ),
    )


__all__ = ["StockCashflowQuarterly"]
