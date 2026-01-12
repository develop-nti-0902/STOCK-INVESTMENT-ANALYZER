from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class BatchExecution(SerialPKMixin, TimestampMixin, Base):
    """バッチ処理実行のサマリを記録するモデル.

    Attributes:
        batch_type (str): バッチの種別（例: 'jpx_all'）
        status (str): ジョブのステータス（例: 'running', 'completed', 'failed'）
        total_stocks (int): 対象銘柄総数
        processed_stocks (int): 処理済銘柄数
        successful_stocks (int): 成功した銘柄数
        failed_stocks (int): 失敗した銘柄数
        start_time (datetime): 実行開始時刻（UTC）
        end_time (Optional[datetime]): 実行終了時刻（UTC）、未完了時は None
        error_message (Optional[str]): 実行中に発生したエラーメッセージ（任意）

    Notes:
        テーブル名は既存スキーマ互換のため `batch_executions` に固定しています。
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

    __table_args__ = (
        Index("idx_batch_executions_status", "status"),
        Index("idx_batch_executions_batch_type", "batch_type"),
        Index("idx_batch_executions_start_time", "start_time"),
    )


__all__ = ["BatchExecution"]
