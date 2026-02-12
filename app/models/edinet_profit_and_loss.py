"""EDINET 損益・キャッシュフローデータモデル（edinet_profit_and_loss）.

EDINET の XBRL 解析結果から抽出した損益計算書とキャッシュフロー計算書データを保持する
SQLAlchemy のモデル定義を提供します。

設計は docs/architecture/edinet_balance_sheet_design.md に準拠します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class EdinetProfitAndLoss(SerialPKMixin, TimestampMixin, Base):
    """EDINET の損益・キャッシュフロー（edinet_profit_and_loss）を表すモデル.

    カラム定義やインデックスは `docs/architecture/edinet_balance_sheet_design.md`に従っています.
    """

    __tablename__ = "edinet_profit_and_loss"

    doc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sec_code: Mapped[str] = mapped_column(String(10), nullable=False)
    filer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    submission_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, default="annual")

    # 財務指標（設計書に従い、operating_profitとepsの2つの主要指標）
    operating_profit: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="営業活動によるキャッシュフロー（百万円）"
    )
    eps: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True, comment="1株当たり当期純利益（円）"
    )

    # メタデータ項目
    candidate_contexts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    candidate_keys: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_pl_doc_id", "doc_id"),
        Index("idx_edinet_pl_sec_code", "sec_code"),
        Index("idx_edinet_pl_period_end", "period_end_date"),
        Index("idx_edinet_pl_sec_period", "sec_code", "period_end_date"),
        UniqueConstraint("sec_code", "period_end_date", name="uq_edinet_pl_sec_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用）."""
        return (
            "<EdinetProfitAndLoss(doc_id="
            f"{self.doc_id!r}, sec_code={self.sec_code!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetProfitAndLoss"]
