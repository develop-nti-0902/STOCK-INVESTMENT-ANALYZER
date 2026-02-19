"""モデル共通基底と mixin を提供するモジュール（core へ移動）."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import CHAR, DateTime, Integer, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def _camel_to_snake(name: str) -> str:
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class Base(DeclarativeBase):
    """__tablename__ を自動生成する宣言的ベースクラス。"""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """サブクラス定義時に `__tablename__` を自動生成します.

        指定がない場合、クラス名を snake_case に変換して設定します。
        """
        if "__tablename__" not in cls.__dict__:
            cls.__tablename__ = _camel_to_snake(cls.__name__)
        super().__init_subclass__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """インスタンスの簡易文字列表現を返します.

        テストやログでの識別に使える短い表現を返します。
        """
        ident = getattr(self, "id", None)
        if ident is not None:
            return f"<{self.__class__.__name__} id={ident!r}>"
        return f"<{self.__class__.__name__}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """このモデルのクラス名を返します（ログやテストで利用）。"""
        return self.__class__.__name__


class GUID(TypeDecorator):  # pylint: disable=too-many-ancestors
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)

    def process_literal_param(self, value, dialect):
        return self.process_bind_param(value, dialect)

    @property
    def python_type(self):
        return uuid.UUID


class SerialPKMixin:
    """整数のシリアル主キーを提供する mixin。"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """インスタンスの簡易文字列表現を返します.

        テストやログでの識別に使える短い表現を返します。
        """
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """この mixin が適用されたモデルのクラス名を返します。"""
        return self.__class__.__name__


class UUIDPKMixin:
    """UUID 主キーを提供する mixin。"""

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """インスタンスの簡易文字列表現を返します.

        テストやログでの識別に使える短い表現を返します。
        """
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """この mixin が適用されたモデルのクラス名を返します。"""
        return self.__class__.__name__


class TimestampMixin:
    """作成日時と更新日時のカラムを追加する mixin。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """作成/更新日時の初期値を設定します.

        明示的な値が与えられていない場合、現在時刻で `created_at`/`updated_at` を初期化します。
        """
        now = datetime.now(timezone.utc)
        if "created_at" not in kwargs or kwargs.get("created_at") is None:
            kwargs["created_at"] = now
        if "updated_at" not in kwargs or kwargs.get("updated_at") is None:
            kwargs["updated_at"] = now
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """インスタンスの簡易文字列表現を返します.

        テストやログでの識別に使える短い表現を返します。
        """
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """この mixin が適用されたモデルのクラス名を返します。"""
        return self.__class__.__name__


__all__ = ["Base", "SerialPKMixin", "UUIDPKMixin", "TimestampMixin"]
