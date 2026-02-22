"""株式分割情報モデル（stock_split）。

シンプルな分割履歴を保持するテーブルを定義します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class StockSplit(SerialPKMixin, TimestampMixin, Base):
    """株式分割（stock_split）モデル.

    カラム:
      - code: 銘柄コード（文字列）
      - effective_date: 発効日
      - ratio_from: 分割前比率（整数）
      - ratio_to: 分割後比率（整数）
    """

    __tablename__ = "stock_split"

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    ratio_from: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ratio_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_stock_split_code", "code"),
        Index("idx_stock_split_effective", "effective_date"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<StockSplit(code={self.code!r}, effective_date={self.effective_date!r})>"


__all__ = ["StockSplit"]
