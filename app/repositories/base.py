"""
Repository層 - 基底クラス

全てのRepositoryクラスの基底となる抽象クラスを定義する。
汎用的なCRUD操作を提供し、SQLAlchemyの非同期セッションを使用する。
仕様書: docs/architecture/layers/data_access_layer.md 3.1章
"""

import inspect
import logging
from abc import ABC
from typing import Any, Dict, Generic, List, Optional, TypeVar, cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from app.utils.database import flush_commit_return

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

    async def _maybe_await(self, value):
        """値が awaitable（例えば AsyncMock）であれば await するヘルパー。

        実運用では AsyncSession のメソッドは通常同期的に None を返しますが、
        テスト環境ではモックが awaitable を返す場合があります。
        このヘルパーは両者に対応するためのものです。
        """
        if inspect.isawaitable(value):
            return await value
        return value

    async def create(self, data: Dict) -> T:
        """新規レコードを作成して返す。

        引数:
            data: モデルのフィールド値を含む辞書

        戻り値:
            作成されたモデルインスタンス

        例外:
            データベース操作や制約違反時に SQLAlchemy の例外が発生する可能性があります。
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instance = self.model(**data)
        try:
            # AsyncSession.add は通常 None を返します。
            # ただしテスト環境では awaitable を返すモックが使われる場合があるため、Any にキャストします。
            maybe_res = cast(Any, self.session.add(instance))
            await self._maybe_await(maybe_res)
            return await flush_commit_return(self.session, instance)
        except SQLAlchemyError as e:
            # flush_commit_return は失敗時に rollback して例外を再送出しますが、
            # ここでも念のためログを残します。
            logger.exception("Failed to create instance: %s", e)
            raise

    async def get(self, record_id: int) -> Optional[T]:
        """IDで単一レコードを取得する。

        引数:
            record_id: レコードの ID

        戻り値:
            見つかったモデルインスタンス、存在しない場合は None
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[T]:
        """ページネーション対応で複数レコードを取得する。

        引数:
            skip: 取得開始のオフセット（デフォルト: 0）
            limit: 取得件数（デフォルト: 100）

        戻り値:
            モデルインスタンスのリスト
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).limit(limit).offset(skip)
        )
        return list(result.scalars().all())

    async def update(self, record_id: int, data: Dict) -> Optional[T]:
        """レコードを更新して更新後のインスタンスを返す。

        引数:
            record_id: 更新対象のレコード ID
            data: 更新するフィールドの辞書

        戻り値:
            更新後のモデルインスタンス、存在しない場合は None

        例外:
            データベース操作や制約違反時に SQLAlchemy の例外が発生します。
        """
        instance = await self.get(record_id)
        if instance is None:
            return None
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        try:
            return await flush_commit_return(self.session, instance)
        except SQLAlchemyError as e:
            logger.exception(
                "Failed to update instance id=%s: %s", record_id, e
            )
            raise

    async def delete(self, record_id: int) -> bool:
        """指定 ID のレコードを削除する。

        引数:
            record_id: 削除対象のレコード ID

        戻り値:
            削除に成功した場合は True、対象が存在しない場合は False

        例外:
            データベース操作に失敗した場合は SQLAlchemy の例外が発生します。
        """
        instance = await self.get(record_id)
        if instance is None:
            return False
        try:
            maybe_res = cast(Any, self.session.delete(instance))
            await self._maybe_await(maybe_res)
            await flush_commit_return(self.session, True)
            return True
        except SQLAlchemyError as e:
            # 削除処理で例外が発生した場合はロールバックを行う
            await self.session.rollback()
            logger.exception(
                "Failed to delete instance id=%s: %s", record_id, e
            )
            raise

    async def bulk_create(self, records: List[dict]) -> List[T]:
        """複数レコードを一括作成する。

        引数:
            records: レコードの辞書リスト

        戻り値:
            作成されたモデルインスタンスのリスト

        例外:
            データベース操作や制約違反時に SQLAlchemy の例外が発生します。
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instances = [self.model(**record) for record in records]
        try:
            maybe_res = cast(Any, self.session.add_all(instances))
            await self._maybe_await(maybe_res)
            return await flush_commit_return(self.session, instances)
        except SQLAlchemyError as e:
            logger.exception("Failed to bulk create instances: %s", e)
            raise

    async def count(self) -> int:
        """モデルテーブルの総件数を返す。"""
        if self.model is None:
            raise ValueError("Repository model is not set")

        stmt = select(sql_count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, record_id: int) -> bool:
        """指定 ID のレコードが存在するかを判定する。"""
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none() is not None
