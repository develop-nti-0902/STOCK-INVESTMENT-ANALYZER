"""アナリスト推奨モデル定義モジュール.

`stock_analyst_recommendations` テーブルに対応する SQLAlchemy モデルを定義します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockAnalystRecommendations(SerialPKMixin, TimestampMixin, Base):
    """アナリスト推奨（`stock_analyst_recommendations`）モデル。

    主なカラムは `symbol`, `period`, `strong_buy`, `buy`, `hold`, `sell`,
    `strong_sell`, `source` などです。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    period: Mapped[Optional[str]] = mapped_column(Date, nullable=False)

    strong_buy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    buy: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hold: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sell: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strong_sell: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("idx_recommendations_symbol_period", "symbol", "period"),
        Index(
            "uq_recommendations_symbol_period_source",
            "symbol",
            "period",
            "source",
            unique=True,
        ),
    )


__all__ = ["StockAnalystRecommendations"]
