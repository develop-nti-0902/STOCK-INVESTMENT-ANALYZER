"""EDINET 損益（edinet_profit_and_loss）モデル.

指定されたスキーマに基づき、損益計算書の主要項目を保持する SQLAlchemy モデルを定義します。
この実装は既存互換性を保たない新規定義として作成されています。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class EdinetProfitAndLoss(SerialPKMixin, TimestampMixin, Base):
    """EDINET の損益データを表すモデル.

    テーブル名: edinet_profit_and_loss
    """

    __tablename__ = "edinet_profit_and_loss"

    # 基本メタ情報
    doc_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sec_code: Mapped[str] = mapped_column(String(10), nullable=False)
    submission_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    report_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="annual", server_default=text("'annual'")
    )

    # 損益主要数値
    net_sales: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    operating_income: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    eps: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # 実際に解析で使用された情報
    candidate_contexts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    candidate_keys: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # 連結フラグ
    is_consolidated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    __table_args__ = (
        Index("idx_edinet_pl_doc_id", "doc_id"),
        Index("idx_edinet_pl_sec_code", "sec_code"),
        Index("idx_edinet_pl_period_end", "period_end_date"),
        UniqueConstraint("sec_code", "period_end_date", name="uq_edinet_pl_sec_period"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return (
            "<EdinetProfitAndLoss(doc_id="
            f"{self.doc_id!r}, sec_code={self.sec_code!r}, "
            f"period_end_date={self.period_end_date!r})>"
        )


__all__ = ["EdinetProfitAndLoss"]
