"""銘柄マスタ更新履歴モデル (移動済み)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin


class StockMasterUpdates(SerialPKMixin, Base):
    """銘柄マスタ更新履歴を表すモデル."""

    update_type: Mapped[str] = mapped_column(String(20), nullable=False)
    total_stocks: Mapped[int] = mapped_column(Integer, nullable=False)
    added_stocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_stocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    removed_stocks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def duration_seconds(self) -> Optional[int]:
        if self.completed_at is None:
            return None
        return int((self.completed_at - self.started_at).total_seconds())


__all__ = ["StockMasterUpdates"]
