"""EDINET 貸借対照表データモデル（edinet_balance_sheets）.

EDINET の XBRL 解析結果から抽出した貸借対照表データを保持する
SQLAlchemy のモデル定義を提供します。

設計は docs/architecture/edinet_balance_sheet_design.md に準拠します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class EdinetBalanceSheet(SerialPKMixin, TimestampMixin, Base):
    """EDINET の貸借対照表（edinet_balance_sheets）を表すモデル.

    カラム定義やインデックスは `docs/architecture/edinet_balance_sheet_design.md`に従っています.
    """

    __tablename__ = "edinet_balance_sheets"

    doc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sec_code: Mapped[str] = mapped_column(String(10), nullable=False)
    filer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submission_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, default="annual")

    total_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    current_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    non_current_assets: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    cash_and_equivalents: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    total_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    current_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    non_current_liabilities: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    short_term_loans: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    long_term_loans: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    total_equity: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    shareholders_equity: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    retained_earnings: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    bps: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    equity_to_asset_ratio: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    candidate_contexts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    candidate_keys: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_balance_doc_id", "doc_id"),
        Index("idx_edinet_balance_sec_code_period", "sec_code", "period_end_date"),
        UniqueConstraint("sec_code", "period_end_date", name="uq_edinet_sec_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            "<EdinetBalanceSheet(doc_id="
            f"{self.doc_id!r}, sec_code={self.sec_code!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetBalanceSheet"]
