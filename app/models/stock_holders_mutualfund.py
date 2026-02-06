"""投資信託保有情報モデル.

このモジュールは `stock_holders_mutualfund` テーブルに対応します.
"""

# pylint: disable=too-few-public-methods

from typing import Optional

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockHoldersMutualfund(Base, SerialPKMixin, TimestampMixin):
    """投資信託の保有情報エントリを表すモデル."""

    __tablename__ = "stock_holders_mutualfund"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    as_of_date: Mapped[Optional[str]] = mapped_column(Date, nullable=False)
    fund_name: Mapped[str] = mapped_column(String(200), nullable=False)
    fund_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fund_shares: Mapped[Optional[int]] = mapped_column(Numeric(20, 0), nullable=True)
    fund_percent: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    reported_shares: Mapped[Optional[int]] = mapped_column(Numeric(20, 0), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    filing_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


Index("idx_mutualfund_symbol", StockHoldersMutualfund.symbol)
Index("idx_mutualfund_asof", StockHoldersMutualfund.as_of_date)
Index("idx_mutualfund_fund", StockHoldersMutualfund.fund_name)
Index(
    "uq_mutualfund_symbol_asof_fund",
    StockHoldersMutualfund.symbol,
    StockHoldersMutualfund.as_of_date,
    StockHoldersMutualfund.fund_name,
    StockHoldersMutualfund.source,
    unique=True,
)
