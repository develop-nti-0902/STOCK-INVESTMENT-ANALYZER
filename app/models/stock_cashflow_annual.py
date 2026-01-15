"""年次キャッシュフロー（stock_cashflow_annual）モデル定義モジュール.

年次ベースのキャッシュフロー計算書主要項目を保存する SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockCashflowAnnual(SerialPKMixin, TimestampMixin, Base):
    """年次キャッシュフローの主要項目を格納するモデル.

    定義は `docs/architecture/layers/data_storage_layer.md` の
    `stock_cashflow_annual` セクションに合わせています。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=True)

    operating_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    investing_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    financing_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    net_change_in_cash: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    free_cashflow: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    cash_and_equivalents_end: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )

    __table_args__ = (
        Index("idx_stock_cashflow_symbol", "symbol"),
        Index("idx_stock_cashflow_year", "fiscal_year"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockCashflowAnnual(symbol="
            + f"{self.symbol!r}, fiscal_year={self.fiscal_year!r})>"
        )


__all__ = ["StockCashflowAnnual"]
