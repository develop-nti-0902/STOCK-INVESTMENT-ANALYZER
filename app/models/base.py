"""モデル共通基底と mixin を提供するモジュール.

このモジュールはプロジェクトで使う SQLAlchemy の Declarative base と
再利用可能な mixin クラスを定義します。テーブル名自動生成や共通カラムを提供します。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _camel_to_snake(name: str) -> str:
    """CamelCase のクラス名を snake_case のテーブル名に変換するユーティリティ.

    Args:
        name (str): クラス名（CamelCase）

    Returns:
        str: スネークケースに変換された文字列
    """
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class Base(DeclarativeBase):
    """プロジェクト共通の Declarative base.

    - 自動でテーブル名をスネークケースに変換して設定する
    - 共通カラムは各モデル側で mixin を組み合わせて提供する設計

    Notes:
        サブクラスで `__tablename__` を明示しなければ、自動でクラス名から生成します。
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """サブクラス初期化時にテーブル名を自動設定します."""
        # サブクラスで明示的に__tablename__がなければ自動でスネークケースを付与
        if "__tablename__" not in cls.__dict__:
            cls.__tablename__ = _camel_to_snake(cls.__name__)
        super().__init_subclass__(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """モデルインスタンスの簡易表現を返す（デバッグ用)."""
        # `id` があれば含める。
        ident = getattr(self, "id", None)
        if ident is not None:
            return f"<{self.__class__.__name__} id={ident!r}>"
        return f"<{self.__class__.__name__}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返すユーティリティメソッド. テストやログで便利."""
        return self.__class__.__name__


class SerialPKMixin:
    """整数の自動増分 ID を提供する mixin.

    Attributes:
        id (int): 自動増分プライマリキー
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用)."""
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返すユーティリティメソッド."""
        return self.__class__.__name__


class UUIDPKMixin:
    """UUID をプライマリキーにするモデル向け mixin.

    Attributes:
        id (uuid.UUID): UUID プライマリキー（デフォルトで uuid.uuid4 を使用）
    """

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用)."""
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返すユーティリティメソッド."""
        return self.__class__.__name__


class TimestampMixin:
    """作成/更新時刻の共通カラムを提供する mixin.

    Attributes:
        created_at (datetime): レコード作成時刻（UTC）
        updated_at (datetime): レコード更新時刻（UTC）

    Notes:
        - クライアントサイドのデフォルトを `__init__` で埋める。
        - DB サーバ側のデフォルト値も `server_default=text("now()")` で確保。
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
        """初期化時に作成/更新時刻のデフォルト値を設定します."""
        now = datetime.now(timezone.utc)
        if "created_at" not in kwargs or kwargs.get("created_at") is None:
            kwargs["created_at"] = now
        if "updated_at" not in kwargs or kwargs.get("updated_at") is None:
            kwargs["updated_at"] = now
        super().__init__(*args, **kwargs)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        """簡易表現を返す（デバッグ用)."""
        # created_at/updated_at を含めず簡潔に表現
        ident = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={ident!r}>"

    def model_name(self) -> str:  # pragma: no cover - trivial
        """モデルのクラス名を返すユーティリティメソッド."""
        return self.__class__.__name__


__all__ = ["Base", "SerialPKMixin", "UUIDPKMixin", "TimestampMixin"]
