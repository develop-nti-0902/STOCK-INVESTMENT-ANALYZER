"""アカウント（ユーザー）テーブルのモデル定義モジュール.

管理用途の `accounts` テーブルに合わせたモデルを定義します。
プロジェクト内の他モデルと同様に `SerialPKMixin` と `TimestampMixin` を利用します.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.core.base import Base, SerialPKMixin, TimestampMixin


class Account(SerialPKMixin, TimestampMixin, Base):
    """アカウント（users）テーブルモデル.

    Attributes:
        email: ユニークなメールアドレス
        hashed_password: ハッシュ化されたパスワード
        full_name: 表示名
        is_active: アカウント有効フラグ
        is_superuser: 管理者フラグ
        last_login: 最終ログイン時刻
        provider: 外部認証プロバイダ名（任意）
        external_id: 外部プロバイダの識別子（任意）
    """

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (Index("idx_account_email", "email"),)

    def __repr__(self) -> str:
        """簡易表現を返す（デバッグ用)."""
        return f"<Account(email={self.email!r}, " f"id={getattr(self, 'id', None)!r})>"


__all__ = ["Account"]
