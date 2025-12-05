from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """プロジェクト共通のDeclarative base。

    - 自動でテーブル名をスネークケースに変換して設定する
    - 共通カラム: `id`, `created_at`, `updated_at`
    - 非同期/同期どちらのエンジンでも利用できるマッピングスタイル
    """

    def __init_subclass__(
        cls, **kwargs: Any
    ) -> None:  # type: ignore[override]
        # サブクラスで明示的に__tablename__がなければ自動でスネークケースを付与
        if "__tablename__" not in cls.__dict__:
            cls.__tablename__ = _camel_to_snake(cls.__name__)
        super().__init_subclass__(**kwargs)


class SerialPKMixin:  # pylint: disable=too-few-public-methods
    """整数の自動増分ID（既存SQLスクリプトの `SERIAL` に対応）。"""

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )


class UUIDPKMixin:  # pylint: disable=too-few-public-methods
    """UUIDプライマリキーを使いたいモデル向けの mixin。"""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:  # pylint: disable=too-few-public-methods
    """created_at / updated_at を提供する mixin。

    - client-side default を __init__ で埋める。
    - server_default に `now()` を指定してDB側のデフォルトも確保。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        now = datetime.now(timezone.utc)
        if "created_at" not in kwargs or kwargs.get("created_at") is None:
            kwargs["created_at"] = now
        if "updated_at" not in kwargs or kwargs.get("updated_at") is None:
            kwargs["updated_at"] = now
        super().__init__(*args, **kwargs)


__all__ = ["Base", "SerialPKMixin", "UUIDPKMixin", "TimestampMixin"]
