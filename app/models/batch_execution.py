from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin


class BatchExecution(SerialPKMixin, Base):
    """バッチ処理の実行サマリを記録するモデル。

    - テーブル名は `batch_executions` に固定している（既存スキーマとの整合性維持）。
    - `job_type` をバッチ種別として扱う。
    """

    __tablename__ = "batch_executions"

    batch_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    # 実行開始 / 終了
    # SQL スクリプトに合わせたカラム名・仕様に変更
    total_stocks: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    successful_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    failed_stocks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
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

    __table_args__ = (
        Index("idx_batch_executions_status", "status"),
        Index("idx_batch_executions_batch_type", "batch_type"),
        Index("idx_batch_executions_start_time", "start_time"),
    )


__all__ = ["BatchExecution"]
