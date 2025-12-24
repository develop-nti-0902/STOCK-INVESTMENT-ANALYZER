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

from app.utils.database import flush_return_with_log
from app.utils.validation import validate_pagination

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

    def __init__(self, session: AsyncSession, model: Optional[type] = None):
        """
        初期化

        Args:
            session: 非同期DBセッション
            model: SQLAlchemyモデルクラス（オプション）
        """
        # 型安全性は将来的に SQLAlchemy Base に束縛した TypeVar に変更する
        # 現状は任意のモデルクラスを受け取るため `Any` として扱う
        # 明示的に model を渡すか、サブクラスがクラス属性/プロパティとして `model` を定義していることを期待する
        # サブクラスが model をプロパティとして定義している場合があるため、
        # 直接 self.model に代入せず、内部的に _model を使用する
        if model is not None:
            self._model: Any = model
        else:
            # サブクラスがクラス属性/プロパティとして model を定義している場合はそれを参照する
            # プロパティの場合は getattr で取得できるが、設定はしない
            self._model = getattr(type(self), "model", None)
            if self._model is None:
                self._model = getattr(self, "model", None)

        self.session = session

        # 注意: サブクラスやテストが `super().__init__(session)` の後で
        # `self._model` を設定できるよう、ここでは例外を投げません。
        # 各メソッドは必要時に `self.model` の存在を検証し、
        # 未設定の場合は明確な `ValueError` を発生させます。

    @property
    def model(self) -> Any:
        """
        SQLAlchemyモデルクラスを取得

        サブクラスでプロパティとしてオーバーライド可能。
        """
        return self._model

    async def _add_and_flush(self, instance: T) -> T:
        """インスタンスをセッションに追加してflushする共通処理。

        テスト環境で session.add が awaitable を返す可能性に対応します。
        トランザクション管理（commit/rollback）はService層で行います。
        """
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
        """複数インスタンスを追加してflushする共通処理。

        トランザクション管理（commit/rollback）はService層で行います。
        """
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
        注意:
            トランザクションのコミットはService層で行ってください。
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instance = self.model(**data)
        return await self._add_and_flush(instance)

    async def upsert(self, data: Dict) -> T:
        """単一レコードの upsert を行うためのインターフェース。

        デフォルト実装は未サポートとして `NotImplementedError` を投げます。
        サブクラスでサポートする場合はこのメソッドをオーバーライドしてください。
        """
        raise NotImplementedError(
            "upsert is not implemented for this repository"
        )

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

        # 引数検証: 共通ユーティリティへ移譲
        validate_pagination(skip, limit)

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
        注意:
            トランザクションのコミットはService層で行ってください。
        """
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
        """指定 ID のレコードを削除する。

        引数:
            record_id: 削除対象のレコード ID

        戻り値:
            削除に成功した場合は True、対象が存在しない場合は False

        例外:
            データベース操作に失敗した場合は SQLAlchemy の例外が発生します。
        注意:
            トランザクションのコミットはService層で行ってください。
        """
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
        """複数レコードを一括作成する。

        引数:
            records: レコードの辞書リスト

        戻り値:
            作成されたモデルインスタンスのリスト

        例外:
            データベース操作や制約違反時に SQLAlchemy の例外が発生します。
        注意:
            トランザクションのコミットはService層で行ってください。
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instances = [self.model(**record) for record in records]
        return await self._add_all_and_flush(instances)

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
