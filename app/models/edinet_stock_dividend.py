"""EDINET 株式配当データモデル（edinet_stock_dividend）.

EDINET の XBRL 解析結果から抽出した年間配当金データを保持する
SQLAlchemy のモデル定義を提供します。

設計は docs/architecture/edinet_balance_sheet_design.md に準拠します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class EdinetStockDividend(SerialPKMixin, TimestampMixin, Base):
    """EDINET の年間配当情報（edinet_stock_dividend）を表すモデル.

    カラム定義やインデックスは edinet の設計に準拠しています。
    """

    __tablename__ = "edinet_stock_dividend"

    doc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sec_code: Mapped[str] = mapped_column(String(10), nullable=False)
    submission_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, default="annual")

    dividend_actual: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="年間配当金（百万円または円など、ソースに依存）"
    )

    candidate_contexts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    candidate_keys: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_sd_doc_id", "doc_id"),
        Index("idx_edinet_sd_sec_code", "sec_code"),
        Index("idx_edinet_sd_period_end", "period_end_date"),
        Index("idx_edinet_sd_sec_period", "sec_code", "period_end_date"),
        UniqueConstraint("sec_code", "period_end_date", name="uq_edinet_sd_sec_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            "<EdinetStockDividend(doc_id="
            f"{self.doc_id!r}, sec_code={self.sec_code!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetStockDividend"]
