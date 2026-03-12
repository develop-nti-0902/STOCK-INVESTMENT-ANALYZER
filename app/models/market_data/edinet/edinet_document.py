"""EDINET ドキュメント（メタデータ）モデル（edinet_document）.

EDINET から取得した財務報告書のメタデータを一元管理するモデルです。
doc_id, sec_code, submission_date, report_type などのメタデータを集約し、
各財務テーブル（損益計算書、キャッシュフロー、配当、貸借対照表）が
このテーブルを外部キー参照します。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class EdinetDocument(SerialPKMixin, TimestampMixin, Base):
    """EDINET ドキュメント（edinet_document）を表すモデル.

    各財務テーブルが参照するメタデータを一元管理します。
    テーブル名: edinet_document
    """

    __tablename__ = "edinet_document"

    # 一意のドキュメント識別子
    doc_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # 証券コード（FK to stock_code_mapping.sec_code）
    # NOTE: 将来、stock_code_mapping テーブルが用意されたら FK に変更可能
    sec_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # 提出日
    submission_date: Mapped[date] = mapped_column(Date, nullable=False)

    # 報告書タイプ（annual, quarterly, etc）
    report_type: Mapped[str] = mapped_column(String(20), nullable=False, default="annual")

    # XBRL 解析メタデータ
    candidate_contexts: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    candidate_keys: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        Index("idx_edinet_doc_doc_id", "doc_id", unique=True),
        Index("idx_edinet_doc_sec_code", "sec_code"),
        Index("idx_edinet_doc_submission_date", "submission_date"),
        UniqueConstraint("doc_id", name="uq_edinet_doc_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        """インスタンスの簡易文字列表現を返します."""
        return (
            f"<EdinetDocument id={self.id!r} doc_id={self.doc_id!r} "
            f"sec_code={self.sec_code!r} submission_date={self.submission_date!r}>"
        )


__all__ = ["EdinetDocument"]
