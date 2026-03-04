"""規模マスターモデル定義モジュール."""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class ScaleMaster(SerialPKMixin, TimestampMixin, Base):
    """規模マスター（L/M/S など）.

    JPX からダウンロードされた一意の規模値を格納します。
    """

    __tablename__ = "scale_master"

    code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (Index("idx_scale_code", "code"),)

    def __repr__(self) -> str:
        """インスタンスの簡易文字列表現を返します."""
        return f"<ScaleMaster(code={self.code!r}, name={self.name!r})>"


__all__ = ["ScaleMaster"]
