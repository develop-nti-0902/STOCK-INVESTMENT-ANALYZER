from typing import Optional

from sqlalchemy import Date, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockInsiderTransactions(Base, SerialPKMixin, TimestampMixin):
    __tablename__ = "stock_insider_transactions"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    transaction_date: Mapped[Optional[str]] = mapped_column(
        Date, nullable=False
    )
    insider_name: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    transaction_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    shares: Mapped[Optional[int]] = mapped_column(
        Numeric(20, 0), nullable=True
    )
    price: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 4), nullable=True
    )
    total_value: Mapped[Optional[float]] = mapped_column(
        Numeric(24, 2), nullable=True
    )
    ownership_after: Mapped[Optional[int]] = mapped_column(
        Numeric(20, 0), nullable=True
    )
    ownership_percent: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    filing_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


Index("idx_insider_symbol", StockInsiderTransactions.symbol)
Index("idx_insider_date", StockInsiderTransactions.transaction_date)
Index("idx_insider_name", StockInsiderTransactions.insider_name)
Index(
    "uq_insider_symbol_name_date_type",
    StockInsiderTransactions.symbol,
    StockInsiderTransactions.insider_name,
    StockInsiderTransactions.transaction_date,
    StockInsiderTransactions.transaction_type,
    unique=True,
)
