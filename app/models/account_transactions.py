"""アカウント取引履歴（account_transactions）テーブルのモデル定義モジュール.

`docs/architecture/layers/data_storage_layer.md` のデータ層定義に合わせ、
管理用の取引履歴テーブルを提供します。既存モデルと同様に `SerialPKMixin` と
`TimestampMixin` を使用し、インデックスを設定します.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, SerialPKMixin, TimestampMixin


class AccountTransactions(SerialPKMixin, TimestampMixin, Base):
    """アカウントに紐づく取引履歴を保持するモデル.

    主に買付・売却・入出金などの履歴を保存します.
    """

    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("account.id"),
        nullable=False,
    )
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    symbol: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    amount: Mapped[Optional[float]] = mapped_column(Numeric(18, 4), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_account_transactions_account", "account_id"),
        Index("idx_account_transactions_symbol", "symbol"),
        Index("idx_account_transactions_executed_at", "executed_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用)."""
        return (
            "<AccountTransactions(account_id="
            f"{self.account_id!r}, "
            f"transaction_type={self.transaction_type!r})>"
        )


__all__ = ["AccountTransactions"]
