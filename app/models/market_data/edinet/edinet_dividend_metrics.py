"""EDINET 配当メトリクス（edinet_dividend_metrics）モデル.

指定されたスキーマに基づき、配当メトリクスの主要項目を保持する SQLAlchemy モデルを定義します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class EdinetDividendMetrics(SerialPKMixin, TimestampMixin, Base):
    """EDINET の配当メトリクスデータを表すモデル.

    テーブル名: edinet_dividend_metrics
    """

    __tablename__ = "edinet_dividend_metrics"

    # EDINET ドキュメントへの外部キー
    edinet_document_id: Mapped[int] = mapped_column(
        ForeignKey("edinet_document.id"), nullable=False
    )

    # 財務データ固有の情報
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 配当メトリクス主要数値
    dividend_actual: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    eps: Mapped[Optional[float]] = mapped_column(Numeric(15, 4), nullable=True)
    payout_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)

    # 連結フラグ
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_dm_document_id", "edinet_document_id"),
        Index("idx_edinet_dm_period_end", "period_end_date"),
        UniqueConstraint("edinet_document_id", "period_end_date", name="uq_edinet_dm_doc_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """Return short representation for debugging."""
        return (
            f"<EdinetDividendMetrics(document_id={self.edinet_document_id!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetDividendMetrics"]
