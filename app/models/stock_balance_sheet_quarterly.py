"""四半期貸借対照表モデル定義モジュール.

`stock_balance_sheet_quarterly` テーブルに対応する SQLAlchemy モデルを定義します。
"""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockBalanceSheetQuarterly(SerialPKMixin, TimestampMixin, Base):
    """四半期貸借対照表（`stock_balance_sheet_quarterly`）モデル.

    主要なカラムを厳選し、必要に応じて `additional_data` で拡張可能とする設計を採用します。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    fiscal_quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=True)

    total_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    current_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    non_current_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    current_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    non_current_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    total_equity: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    retained_earnings: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    __table_args__ = (
        Index("idx_stock_bsq_symbol", "symbol"),
        Index("idx_stock_bsq_year_quarter", "fiscal_year", "fiscal_quarter"),
        Index(
            "uq_stock_bsq_symbol_year_quarter",
            "symbol",
            "fiscal_year",
            "fiscal_quarter",
            unique=True,
        ),
    )


__all__ = ["StockBalanceSheetQuarterly"]
