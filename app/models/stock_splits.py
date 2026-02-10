"""株式分割情報（stock_splits）モデル定義モジュール.

`docs/architecture/layers/data_storage_layer.md` の定義に合わせた
SQLAlchemy モデルを提供します。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Date, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class StockSplits(SerialPKMixin, TimestampMixin, Base):
    """企業の株式分割／併合の履歴を保持するモデル.

    Notes:
        - 同一銘柄・同日で重複しないよう `(symbol, split_date)` のユニーク制約を
          DB 側で想定しています（アプリ層ではインデックスのみ設定）。
    """

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    split_date: Mapped[str] = mapped_column(Date, nullable=False)
    ratio: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    split_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_stock_splits_symbol", "symbol"),
        Index("idx_stock_splits_date", "split_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return "<StockSplits(symbol=" + f"{self.symbol!r}, split_date={self.split_date!r})>"


__all__ = ["StockSplits"]
