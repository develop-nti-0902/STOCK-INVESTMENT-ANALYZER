"""年次貸借対照表（stock_balance_sheet_annual）モデル定義モジュール.

年次ベースの貸借対照表主要項目を保存する SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockBalanceSheetAnnual(SerialPKMixin, TimestampMixin, Base):
    """年次貸借対照表の主要項目を格納するモデル.

    カラム定義は `docs/architecture/layers/data_storage_layer.md` の
    `stock_balance_sheet_annual` セクションに合わせています。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=True)

    total_assets: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    current_assets: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    non_current_assets: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    total_liabilities: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    current_liabilities: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    non_current_liabilities: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    total_equity: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    retained_earnings: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )

    __table_args__ = (
        Index("idx_stock_balancesheet_symbol", "symbol"),
        Index("idx_stock_balancesheet_year", "fiscal_year"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockBalanceSheetAnnual(symbol="
            + f"{self.symbol!r}, fiscal_year={self.fiscal_year!r})>"
        )


__all__ = ["StockBalanceSheetAnnual"]
