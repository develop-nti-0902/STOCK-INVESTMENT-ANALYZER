"""日経225日足データモデル."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class Nikkei2251d(SerialPKMixin, TimestampMixin, Base):  # pylint: disable=too-few-public-methods
    """日経225日足データモデル.

    Attributes:
        timestamp: タイムスタンプ（timezone=True）— ユニーク制約
        open: 始値
        high: 高値
        low: 安値
        close: 終値
        adj_close: 調整終値（Nullable）
        volume: 出来高
    """

    __tablename__ = "nikkei225_1d"

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("timestamp", name="uix_nikkei225_1d_timestamp"),
        Index("idx_nikkei225_1d_timestamp", "timestamp"),
    )
