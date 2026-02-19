"""Repository層 - 基底クラス（core 配下へ移動）.

移動元: app/repositories/base.py の内容をそのまま移設しています。
"""

import inspect
import logging
from abc import ABC
from typing import Any, Dict, Generic, List, Optional, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from app.exceptions.validation import ValidationError
from app.utils.database import flush_return_with_log
from app.utils.validation import validate_pagination

# 型パラメータ: モデルの型
T = TypeVar("T")


logger = logging.getLogger(__name__)


class BaseRepository(ABC, Generic[T]):
    """汎用的な CRUD 操作を提供する Repository の基底クラス.

    Attributes:
        model (type[T]): SQLAlchemy モデルクラス
        session (AsyncSession): 非同期 DB セッション

    Type Parameters:
        T: SQLAlchemy モデルの型
    """

    def __init__(self, session: AsyncSession, model: Optional[type] = None):
        """初期化.

        Args:
            session (AsyncSession): 非同期 DB セッション
            model (Optional[type]): SQLAlchemy モデルクラス（省略可）
        """
        if model is not None:
            self._model: Any = model
        else:
            self._model = getattr(type(self), "model", None)
            if self._model is None:
                self._model = getattr(self, "model", None)

        self.session = session

    @property
    def model(self) -> Any:
        """SQLAlchemy モデルクラスを返すプロパティ.

        サブクラスでオーバーライド可能。
        """
        return self._model

    async def _add_and_flush(self, instance: T) -> T:
        try:
            maybe_res = cast(Any, self.session.add(instance))
            await self._maybe_await(maybe_res)
        except SQLAlchemyError as e:
            logger.exception("Failed to add instance: %s", e)
            raise

        return await flush_return_with_log(
            self.session, instance, logger, "Failed to flush instance"
        )

    async def _add_all_and_flush(self, instances: List[T]) -> List[T]:
        try:
            maybe_res = cast(Any, self.session.add_all(instances))
            await self._maybe_await(maybe_res)
        except SQLAlchemyError as e:
            logger.exception("Failed to add_all instances: %s", e)
            raise

        return await flush_return_with_log(
            self.session,
            instances,
            logger,
            "Failed to flush instances",
        )

    async def _maybe_await(self, value) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    async def create(self, data: Dict) -> T:
        """新しいレコードを作成して永続化し、作成済インスタンスを返します.

        Args:
            data: モデル初期化に使用するフィールド辞書

        Returns:
            作成されたモデルインスタンス
        """
        if self.model is None:
            raise ValidationError(message="Repository model is not set")

        instance = self.model(**data)
        return await self._add_and_flush(instance)

    async def upsert(self, data: Dict) -> T:
        """（必要に応じて）レコードを挿入または更新します.

        サブクラスで実装してください。デフォルトは未実装です。
        """
        raise NotImplementedError("upsert is not implemented for this repository")

    async def get(self, record_id: int) -> Optional[T]:
        """ID による単一レコード検索を行い、見つからなければ None を返します."""
        if self.model is None:
            raise ValidationError(message="Repository model is not set")

        result = await self.session.execute(select(self.model).where(self.model.id == record_id))
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[T]:
        """複数レコードをページネーションありで取得してリストで返します."""
        if self.model is None:
            raise ValidationError(message="Repository model is not set")

        validate_pagination(skip, limit)

        result = await self.session.execute(select(self.model).limit(limit).offset(skip))
        return list(result.scalars().all())

    async def update(self, record_id: int, data: Dict) -> Optional[T]:
        """既存レコードを更新して更新後のインスタンスを返します。存在しなければ None を返します."""
        instance = await self.get(record_id)
        if instance is None:
            return None
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush updated instance id=%s",
            record_id,
        )

    async def delete(self, record_id: int) -> bool:
        """指定 ID のレコードを削除し、削除成功なら True を返します."""
        instance = await self.get(record_id)
        if instance is None:
            return False
        try:
            maybe_res = cast(Any, self.session.delete(instance))
            await self._maybe_await(maybe_res)
        except SQLAlchemyError as e:
            logger.exception("Failed to delete instance: %s", e)
            raise

        return await flush_return_with_log(
            self.session,
            True,
            logger,
            "Failed to flush deleted instance id=%s",
            record_id,
        )

    async def bulk_create(self, records: List[dict]) -> List[T]:
        """複数レコードを一括作成して作成済インスタンスのリストを返します."""
        if self.model is None:
            raise ValidationError(message="Repository model is not set")

        instances = [self.model(**record) for record in records]
        return await self._add_all_and_flush(instances)

    async def count(self) -> int:
        """対象モデルの総レコード数を返します."""
        if self.model is None:
            raise ValidationError(message="Repository model is not set")

        stmt = select(sql_count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, record_id: int) -> bool:
        """指定 ID のレコードが存在するかどうかを返します."""
        if self.model is None:
            raise ValidationError(message="Repository model is not set")

        result = await self.session.execute(select(self.model).where(self.model.id == record_id))
        return result.scalar_one_or_none() is not None
