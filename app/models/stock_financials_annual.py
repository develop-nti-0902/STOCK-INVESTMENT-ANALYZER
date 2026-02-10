"""年次財務指標（stock_financials_annual）モデル定義モジュール.

年次ベースで標準化した財務指標を保持するための SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockFinancialsAnnual(SerialPKMixin, TimestampMixin, Base):
    """年次財務指標を格納するモデル.

    カラム定義は `docs/architecture/layers/data_storage_layer.md` の
    `stock_financials_annual` セクションに合わせています。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end: Mapped[Optional[str]] = mapped_column(Date, nullable=True)

    revenue: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    net_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    basic_eps: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    roe: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    roa: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    total_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    total_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    dividends_per_share: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)

    __table_args__ = (
        Index("idx_stock_finann_symbol", "symbol"),
        Index("idx_stock_finann_year", "fiscal_year"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            "<StockFinancialsAnnual(symbol="
            + f"{self.symbol!r}, fiscal_year={self.fiscal_year!r})>"
        )


__all__ = ["StockFinancialsAnnual"]
