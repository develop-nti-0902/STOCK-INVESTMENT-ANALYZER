"""EDINET 株式配当データモデル（edinet_stock_dividend）.

EDINET の XBRL 解析結果から抽出した年間配当金データを保持する
SQLAlchemy のモデル定義を提供します。

設計は docs/architecture/edinet_balance_sheet_design.md に準拠します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class EdinetStockDividend(SerialPKMixin, TimestampMixin, Base):
    """EDINET の年間配当情報（edinet_stock_dividend）を表すモデル.

    カラム定義やインデックスは edinet の設計に準拠しています。
    """

    __tablename__ = "edinet_stock_dividend"

    # EDINET ドキュメントへの外部キー
    edinet_document_id: Mapped[int] = mapped_column(
        ForeignKey("edinet_document.id"), nullable=False
    )

    # 財務データ固有の情報
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 配当金データ
    dividend_actual: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="年間配当金（百万円または円など、ソースに依存）"
    )

    dividend_adj: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2),
        nullable=True,
        comment="調整後年間配当金（百万円または円など、ソースに依存）",
    )

    # 連結フラグ
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_sd_document_id", "edinet_document_id"),
        Index("idx_edinet_sd_period_end", "period_end_date"),
        UniqueConstraint("edinet_document_id", "period_end_date", name="uq_edinet_sd_doc_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            f"<EdinetStockDividend(document_id={self.edinet_document_id!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetStockDividend"]
