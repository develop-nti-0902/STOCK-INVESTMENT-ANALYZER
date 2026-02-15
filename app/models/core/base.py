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
    def __init_subclass__(cls, **kwargs: Any) -> None:
        if "__tablename__" not in cls.__dict__:
            cls.__tablename__ = _camel_to_snake(cls.__name__)
        super().__init_subclass__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        ident = getattr(self, "id", None)
        if ident is not None:
            return f"<{self.__class__.__name__} id={ident!r}>"
        return f"<{self.__class__.__name__}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
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
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        return self.__class__.__name__


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        return self.__class__.__name__


class TimestampMixin:
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
        now = datetime.now(timezone.utc)
        if "created_at" not in kwargs or kwargs.get("created_at") is None:
            kwargs["created_at"] = now
        if "updated_at" not in kwargs or kwargs.get("updated_at") is None:
            kwargs["updated_at"] = now
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        return self.__class__.__name__


__all__ = ["Base", "SerialPKMixin", "UUIDPKMixin", "TimestampMixin"]
