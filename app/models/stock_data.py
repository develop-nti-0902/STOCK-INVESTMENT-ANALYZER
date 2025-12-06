from __future__ import annotations

from datetime import date as DateType
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin

# pylint: disable=too-few-public-methods


class _CommonPriceColumns:
    open: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class Stocks1m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_1m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", name="uix_stocks_1m_symbol_timestamp"
        ),
        Index("idx_stocks_1m_timestamp", "timestamp"),
    )


class Stocks5m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_5m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", name="uix_stocks_5m_symbol_timestamp"
        ),
        Index("idx_stocks_5m_timestamp", "timestamp"),
    )


class Stocks15m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_15m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", name="uix_stocks_15m_symbol_timestamp"
        ),
        Index("idx_stocks_15m_timestamp", "timestamp"),
    )


class Stocks30m(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_30m"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey(
            "stock_master.stock_code",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", name="uix_stocks_30m_symbol_timestamp"
        ),
        Index("idx_stocks_30m_timestamp", "timestamp"),
    )


class Stocks1h(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_1h"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", name="uix_stocks_1h_symbol_timestamp"
        ),
        Index("idx_stocks_1h_timestamp", "timestamp"),
    )


# 日次・週次・月次は Date を使用
class Stocks1d(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_1d"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[DateType] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uix_stocks_1d_symbol_date"),
        Index("idx_stocks_1d_date", "date"),
    )


class Stocks1wk(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_1wk"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[DateType] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uix_stocks_1wk_symbol_date"),
        Index("idx_stocks_1wk_date", "date"),
    )


class Stocks1mo(SerialPKMixin, TimestampMixin, Base, _CommonPriceColumns):
    __tablename__ = "stocks_1mo"

    symbol: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_master.stock_code", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[DateType] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uix_stocks_1mo_symbol_date"),
        Index("idx_stocks_1mo_date", "date"),
    )


# Exported names are managed in `app/models/__init__.py`
