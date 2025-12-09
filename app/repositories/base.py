"""
Repository層 - 基底クラス

全てのRepositoryクラスの基底となる抽象クラスを定義する。
汎用的なCRUD操作を提供し、SQLAlchemyの非同期セッションを使用する。
仕様書: docs/architecture/layers/data_access_layer.md 3.1章
"""

import logging
from abc import ABC
from typing import Any, Dict, Generic, List, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

# 型パラメータ: モデルの型
T = TypeVar("T")


logger = logging.getLogger(__name__)


class BaseRepository(ABC, Generic[T]):
    """
    Repository基底クラス（汎用CRUD操作提供）

    全てのRepositoryクラスの基底クラスとして、共通のCRUD操作を提供します。
    SQLAlchemyの非同期セッションを使用し、型安全なデータアクセスを実現します。

    Attributes:
        model (type[T]): SQLAlchemyモデルクラス
        session (AsyncSession): 非同期DBセッション

    Type Parameters:
        T: SQLAlchemyモデルの型（将来的にはapp.models.base.Baseにbound）
    """

    def __init__(self, session: AsyncSession):
        """
        初期化

        Args:
            session: 非同期DBセッション
        """
        # 型安全性は将来的に SQLAlchemy Base に束縛した TypeVar に変更する
        # 現状は任意のモデルクラスを受け取るため `Any` として扱う
        self.model: Any = getattr(self, "model", None)
        self.session = session

    async def create(self, data: Dict) -> T:
        """
        新規レコード作成

        Args:
            data: モデルのフィールド値を含む辞書

        Returns:
            T: 作成されたモデルインスタンス

        Raises:
            DatabaseError: データベース操作に失敗した場合
            ConstraintViolationError: 制約違反の場合
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instance = self.model(**data)
        try:
            self.session.add(instance)
            await self.session.flush()
            await self.session.commit()
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception("Failed to create instance: %s", e)
            raise

    async def get(self, record_id: int) -> Optional[T]:
        """
        ID検索

        Args:
            record_id: レコードID

        Returns:
            Optional[T]: モデルインスタンス、見つからない場合はNone

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[T]:
        """
        全件取得（ページネーション対応）

        Args:
            limit: 取得件数（デフォルト: 100）
            offset: オフセット（デフォルト: 0）

        Returns:
            List[T]: モデルインスタンスのリスト

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).limit(limit).offset(skip)
        )
        return list(result.scalars().all())

    async def update(self, record_id: int, data: Dict) -> Optional[T]:
        """
        レコード更新

        Args:
            record_id: レコードID
            **kwargs: 更新するフィールド値

        Returns:
            Optional[T]: 更新後のモデルインスタンス、見つからない場合はNone

        Raises:
            DatabaseError: データベース操作に失敗した場合
            ConstraintViolationError: 制約違反の場合
        """
        instance = await self.get(record_id)
        if instance is None:
            return None
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        try:
            await self.session.flush()
            await self.session.commit()
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception(
                "Failed to update instance id=%s: %s", record_id, e
            )
            raise

    async def delete(self, record_id: int) -> bool:
        """
        レコード削除

        Args:
            record_id: レコードID

        Returns:
            bool: 削除成功時True、レコードが見つからない場合False

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        instance = await self.get(record_id)
        if instance is None:
            return False
        try:
            await self.session.delete(instance)
            await self.session.flush()
            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception(
                "Failed to delete instance id=%s: %s", record_id, e
            )
            raise

    async def bulk_create(self, records: List[dict]) -> List[T]:
        """
        一括作成

        Args:
            records: レコードのリスト（辞書形式）

        Returns:
            List[T]: 作成されたモデルインスタンスのリスト

        Raises:
            DatabaseError: データベース操作に失敗した場合
            ConstraintViolationError: 制約違反の場合
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instances = [self.model(**record) for record in records]
        try:
            self.session.add_all(instances)
            await self.session.flush()
            await self.session.commit()
            return instances
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception("Failed to bulk create instances: %s", e)
            raise

    async def count(self) -> int:
        """
        全件数取得

        Returns:
            int: レコード数

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        stmt = select(sql_count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, record_id: int) -> bool:
        """指定IDのレコードが存在するかを判定する"""
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none() is not None
