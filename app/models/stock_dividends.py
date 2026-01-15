"""配当情報（stock_dividends）モデル定義モジュール.

`docs/architecture/layers/data_storage_layer.md` の定義に合わせた
SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockDividends(SerialPKMixin, TimestampMixin, Base):
    """配当支払い履歴を保持するモデル.

    Notes:
        - `(symbol, ex_date)` のユニーク制約を DB 側で想定しています。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    ex_date: Mapped[str] = mapped_column(Date, nullable=False)
    record_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    payment_date: Mapped[Optional[str]] = mapped_column(Date, nullable=True)
    declaration_date: Mapped[Optional[str]] = mapped_column(
        Date, nullable=True
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    frequency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        Index("idx_stock_dividends_symbol", "symbol"),
        Index("idx_stock_dividends_exdate", "ex_date"),
        Index("idx_stock_dividends_payment", "payment_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<StockDividends(symbol="
            + f"{self.symbol!r}, ex_date={self.ex_date!r})>"
        )


__all__ = ["StockDividends"]
