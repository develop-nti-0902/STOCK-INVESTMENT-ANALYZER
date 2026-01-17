from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SerialPKMixin


class BatchExecutionDetails(SerialPKMixin, Base):
    """バッチ進捗を時間軸（タイムフレーム）単位で集計するモデル。

    設計変更: 大量レコード（銘柄毎）を避け、`batch_execution` ごとに各 `interval` の
    集計（`total_stocks`, `processed_stocks` 等）を記録します。これによりAPIでの進捗
    照会が低コストになります。
    """

    batch_execution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("batch_executions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 例: '1d', '1h', '1m'
    interval: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 集計値（ジョブ開始時に total_stocks をセット、処理中は processed_stocks を更新）
    total_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    processed_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    successful_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    failed_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    start_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    # リレーション（読み取り利便性）
    batch_execution = relationship(
        "BatchExecution", backref="details", passive_deletes=True
    )

    def to_dict(self) -> dict:
        """モデルのフィールドを辞書で返す."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def progress_summary(self) -> str:
        """簡易的な進捗要約を返す。例: '12/100 processed'"""
        return f"{self.processed_stocks}/{self.total_stocks} processed"

    __table_args__ = (
        Index("idx_batch_execution_details_batch_id", "batch_execution_id"),
        Index("idx_batch_execution_details_interval", "interval"),
        Index("idx_batch_execution_details_status", "status"),
        Index(
            "idx_batch_execution_details_batch_interval",
            "batch_execution_id",
            "interval",
        ),
    )


__all__ = ["BatchExecutionDetails"]
