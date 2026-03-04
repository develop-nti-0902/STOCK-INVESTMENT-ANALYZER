"""市場区分マスターモデル定義モジュール."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class MarketCategoryMaster(SerialPKMixin, TimestampMixin, Base):
    """市場区分マスター（Prime/Standard/Growth など）.

    JPX からダウンロードされた一意の市場区分値を格納します。
    """

    __tablename__ = "market_category_master"

    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (Index("idx_market_category_code", "code"),)

    def __repr__(self) -> str:
        """インスタンスの簡易文字列表現を返します."""
        return f"<MarketCategoryMaster(code={self.code!r}, name={self.name!r})>"


__all__ = ["MarketCategoryMaster"]
