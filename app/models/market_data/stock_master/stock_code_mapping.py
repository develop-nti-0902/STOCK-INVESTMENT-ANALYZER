"""JPX 株式コードと EDINET 提出企業コードのマッピングモデル."""

from __future__ import annotations

from sqlalchemy import Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class StockCodeMapping(SerialPKMixin, TimestampMixin, Base):
    """JPX 株式コード（stock_code）と EDINET 提出企業コード（sec_code）の対応関係を管理.

    1つの JPX 企業が複数の EDINET 企業コードを持つ可能性に対応します。
    """

    __tablename__ = "stock_code_mapping"

    stock_code: Mapped[str] = mapped_column(String(10), nullable=False)
    sec_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    __table_args__ = (
        UniqueConstraint("stock_code", "sec_code", name="uq_stock_code_mapping"),
        Index("idx_stock_code_mapping_stock_code", "stock_code"),
        Index("idx_stock_code_mapping_sec_code", "sec_code"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """デバッグ用表示を返します."""
        return f"<StockCodeMapping(stock_code={self.stock_code!r}, " f"sec_code={self.sec_code!r})>"


__all__ = ["StockCodeMapping"]
