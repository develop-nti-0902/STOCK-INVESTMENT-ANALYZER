"""EDINET 損益（edinet_profit_and_loss）モデル.

指定されたスキーマに基づき、損益計算書の主要項目を保持する SQLAlchemy モデルを定義します。
この実装は既存互換性を保たない新規定義として作成されています。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class EdinetProfitAndLoss(SerialPKMixin, TimestampMixin, Base):
    """EDINET の損益データを表すモデル.

    テーブル名: edinet_profit_and_loss
    """

    __tablename__ = "edinet_profit_and_loss"

    # EDINET ドキュメントへの外部キー
    edinet_document_id: Mapped[int] = mapped_column(
        ForeignKey("edinet_document.id"), nullable=False
    )

    # 財務データ固有の情報
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 損益主要数値
    net_sales: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    eps: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # 連結フラグ
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_pl_document_id", "edinet_document_id"),
        Index("idx_edinet_pl_period_end", "period_end_date"),
        UniqueConstraint("edinet_document_id", "period_end_date", name="uq_edinet_pl_doc_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return short representation for debugging."""
        return (
            f"<EdinetProfitAndLoss(document_id={self.edinet_document_id!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetProfitAndLoss"]
