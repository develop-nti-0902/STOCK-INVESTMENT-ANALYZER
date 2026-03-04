"""業種（17分類）マスターモデル定義モジュール."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class Sector17Master(SerialPKMixin, TimestampMixin, Base):
    """業種（17分類）マスター.

    JPX からダウンロードされた業種コード（17分類）とその名称を格納します。
    """

    __tablename__ = "sector_17_master"

    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (Index("idx_sector_17_code", "code"),)

    def __repr__(self) -> str:
        """インスタンスの簡易文字列表現を返します."""
        return f"<Sector17Master(code={self.code!r}, name={self.name!r})>"


__all__ = ["Sector17Master"]
