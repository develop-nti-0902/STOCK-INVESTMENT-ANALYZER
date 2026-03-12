"""EDINET cash flow data model (edinet_cash_flow_statement).

EDINET の XBRL 解析結果から抽出したキャッシュフロー計算書データを保持する
SQLAlchemy のモデル定義を提供します。

設計は docs/architecture/edinet_balance_sheet_design.md に準拠します.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class EdinetCashFlowStatement(SerialPKMixin, TimestampMixin, Base):
    """EDINET のキャッシュフロー計算書（edinet_cash_flow_statement）を表すモデル.

    カラム定義やインデックスは `docs/architecture/edinet_balance_sheet_design.md`に従っています.
    """

    __tablename__ = "edinet_cash_flow_statement"

    # EDINET ドキュメントへの外部キー
    edinet_document_id: Mapped[int] = mapped_column(
        ForeignKey("edinet_document.id"), nullable=False
    )

    # 財務データ固有の情報
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 財務指標
    operating_cf: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="営業キャッシュフロー（百万円）"
    )

    # 連結フラグ
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_cfs_document_id", "edinet_document_id"),
        Index("idx_edinet_cfs_period_end", "period_end_date"),
        UniqueConstraint("edinet_document_id", "period_end_date", name="uq_edinet_cfs_doc_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            f"<EdinetCashFlowStatement(document_id={self.edinet_document_id!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetCashFlowStatement"]
