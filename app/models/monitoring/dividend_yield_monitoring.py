"""配当利回り監視結果を保持するデータモデル."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class DividendYieldMonitoring(
    SerialPKMixin, TimestampMixin, Base
):  # pylint: disable=too-few-public-methods
    """配当利回り監視結果を保存するテーブル定義."""

    sec_code: Mapped[str] = mapped_column(String(10), nullable=False)
    monitoring_date: Mapped[date] = mapped_column(Date, nullable=False)
    latest_dividend_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    latest_stock_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    dividend_yield: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    purchase_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    screening_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    screening_total_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stock_price_source_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    dividend_source_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("sec_code", "monitoring_date", name="uq_dividend_yield_monitoring"),
        Index("idx_dividend_yield_monitoring_date", "monitoring_date"),
        Index("idx_dividend_yield_monitoring_purchase_level", "purchase_level"),
        Index("idx_dividend_yield_monitoring_yield", "dividend_yield"),
    )


__all__ = ["DividendYieldMonitoring"]
