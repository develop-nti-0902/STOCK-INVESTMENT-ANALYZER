"""企業財務情報（stock_financial_info）モデル定義モジュール.

yfinance の `financials` / `quarterly_financials` 等から取得する財務データを
格納するための SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockFinancialInfo(SerialPKMixin, TimestampMixin, Base):
    """企業の財務情報を格納するモデル.

    カラム定義は `docs/architecture/layers/data_storage_layer.md` の
    `stock_financial_info` セクションに合わせています。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    total_revenue: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    gross_profit: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    net_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    basic_eps: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    diluted_eps: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    total_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    cash_and_cash_equivalents: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    operating_cashflow: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    free_cashflow: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    __table_args__ = (
        Index("idx_stock_financial_symbol", "symbol"),
        Index("idx_stock_financial_fiscal", "fiscal_year"),
        Index("idx_stock_financial_period", "period_end"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            "<StockFinancialInfo(symbol=" + f"{self.symbol!r}, fiscal_year={self.fiscal_year!r})>"
        )


__all__ = ["StockFinancialInfo"]
