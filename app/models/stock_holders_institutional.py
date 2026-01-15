"""機関投資家保有情報モデル定義モジュール.

`stock_holders_institutional` テーブルに対応する SQLAlchemy モデルを定義します。
"""

# pylint: disable=too-few-public-methods

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockHoldersInstitutional(SerialPKMixin, TimestampMixin, Base):
    """機関投資家保有情報（`stock_holders_institutional`）モデル。"""

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    as_of_date: Mapped[Optional[str]] = mapped_column(Date, nullable=False)
    holder_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    shares: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    value: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pct_held: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 4), nullable=True
    )

    __table_args__ = (
        Index("idx_institutional_symbol", "symbol"),
        Index("idx_institutional_asof", "as_of_date"),
        Index("idx_institutional_holder", "holder_name"),
        Index(
            "uq_institutional_symbol_asof_holder",
            "symbol",
            "as_of_date",
            "holder_name",
            unique=True,
        ),
    )


__all__ = ["StockHoldersInstitutional"]
