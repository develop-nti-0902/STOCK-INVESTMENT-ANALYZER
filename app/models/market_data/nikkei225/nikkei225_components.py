"""日経225構成銘柄モデル."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class Nikkei225Component(
    SerialPKMixin, TimestampMixin, Base
):  # pylint: disable=too-few-public-methods
    """日経225構成銘柄マスター.

    銘柄属性（名称、業種）はSTOCK_MASTERで管理。
    本テーブルは構成メンバーシップと指数計算用係数のみ保有。
    """

    __tablename__ = "nikkei225_components"

    stock_code: Mapped[str] = mapped_column(
        String(4),
        ForeignKey("stock_master.stock_code"),
        nullable=False,
    )
    price_adjustment_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 1),
        nullable=False,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("stock_code", "effective_date", name="uq_nikkei225_code_date"),
        Index("idx_nikkei225_stock_code", "stock_code"),
        Index("idx_nikkei225_effective_date", "effective_date"),
    )
