"""EDINET 貸借対照表（edinet_balance_sheet）モデル.

指定されたスキーマに基づき、貸借対照表の主要項目を保持する SQLAlchemy モデルを定義します。
この実装は既存互換性を保たない新規定義として作成されています。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class EdinetBalanceSheet(SerialPKMixin, TimestampMixin, Base):
    """EDINET の貸借対照表データを表すモデル.

    テーブル名: edinet_balance_sheet
    """

    __tablename__ = "edinet_balance_sheet"

    # EDINET ドキュメントへの外部キー
    edinet_document_id: Mapped[int] = mapped_column(
        ForeignKey("edinet_document.id"), nullable=False
    )

    # 財務データ固有の情報
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 貸借対照表主要数値
    total_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    net_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    shareholders_equity: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    bps: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    equity_ratio: Mapped[Optional[float]] = mapped_column(Numeric(20, 6), nullable=True)

    # 連結フラグ
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_bs_document_id", "edinet_document_id"),
        Index("idx_edinet_bs_period_end", "period_end_date"),
        UniqueConstraint("edinet_document_id", "period_end_date", name="uq_edinet_bs_doc_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return short representation for debugging."""
        return (
            f"<EdinetBalanceSheet(document_id={self.edinet_document_id!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetBalanceSheet"]
