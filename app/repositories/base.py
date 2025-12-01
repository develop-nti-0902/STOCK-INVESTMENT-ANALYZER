"""
Repository層 - 基底クラス

全てのRepositoryクラスの基底となる抽象クラスを定義する。
汎用的なCRUD操作を提供し、SQLAlchemyの非同期セッションを使用する。
仕様書: docs/architecture/layers/data_access_layer.md 3.1章
"""

from abc import ABC
from typing import Generic, List, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

# SQLAlchemyのBaseモデルを想定した型変数
# 実際のBaseクラスが定義されたら、bound=Baseに変更予定
T = TypeVar("T")


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

    def __init__(self, model: type[T], session: AsyncSession):
        """
        初期化

        Args:
            model: SQLAlchemyモデルクラス
            session: 非同期DBセッション
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> T:
        """
        新規レコード作成

        Args:
            **kwargs: モデルのフィールド値

        Returns:
            T: 作成されたモデルインスタンス

        Raises:
            DatabaseError: データベース操作に失敗した場合
            ConstraintViolationError: 制約違反の場合
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_by_id(self, record_id: int) -> Optional[T]:
        """
        ID検索

        Args:
            record_id: レコードID

        Returns:
            Optional[T]: モデルインスタンス、見つからない場合はNone

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == record_id
            )  # type: ignore
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
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
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, record_id: int, **kwargs) -> Optional[T]:
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
        instance = await self.get_by_id(record_id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        return instance

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
        instance = await self.get_by_id(record_id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True

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
        instances = [self.model(**record) for record in records]
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def count_all(self) -> int:
        """
        全件数取得

        Returns:
            int: レコード数

        Raises:
            DatabaseError: データベース操作に失敗した場合
        """
        stmt = select(sql_count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()
