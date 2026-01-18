"""企業基本情報（stock_basic_info）モデル定義モジュール.

yfinance の `Ticker.info` から取得する企業基本情報を保持するための
SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockBasicInfo(SerialPKMixin, TimestampMixin, Base):
    """企業基本情報を保持するモデル.

    Fields are aligned with docs/architecture/layers/data_storage_layer.md
    for `stock_basic_info`.
    """

    symbol: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True
    )
    short_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    long_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    full_time_employees: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    __table_args__ = (
        Index("idx_stock_basic_sector", "sector"),
        Index("idx_stock_basic_industry", "industry"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockBasicInfo(symbol="
            + f"{self.symbol!r}, short_name={self.short_name!r})>"
        )


__all__ = ["StockBasicInfo"]
