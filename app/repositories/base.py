"""Repository層 - 基底クラス.

全ての Repository クラスの基底となる抽象クラスを提供します。汎用的な CRUD 操作を定義し、
SQLAlchemy の非同期セッションを利用したデータアクセスをサポートします。

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
        """SQLAlchemy モデルクラスを返すプロパティ.

        サブクラスでオーバーライド可能。
        """
        return self._model

    async def _add_and_flush(self, instance: T) -> T:
        """インスタンスをセッションに追加して flush するヘルパー.

        テストでの awaitable な戻り値にも対応します。トランザクション制御は上位層で行います。

        Args:
            instance (T): 追加するモデルインスタンス

        Returns:
            T: フラッシュ後のインスタンス
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
        """複数インスタンスを追加して flush するヘルパー.

        Args:
            instances (List[T]): 追加するインスタンスリスト

        Returns:
            List[T]: フラッシュ後のインスタンスリスト
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
        """値が awaitable なら await してその結果を返すヘルパー.

        テスト環境のモックなど awaitable な戻り値にも対応します。

        Args:
            value: awaitable かもしれないオブジェクト

        Returns:
            Any: 処理結果
        """
        if inspect.isawaitable(value):
            return await value
        return value

    async def create(self, data: Dict) -> T:
        """新規レコードを作成して返す.

        Args:
            data (Dict): モデルのフィールド値を含む辞書

        Returns:
            T: 作成されたモデルインスタンス

        Raises:
            SQLAlchemyError: DB 操作中の例外が発生する可能性があります

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instance = self.model(**data)
        return await self._add_and_flush(instance)

    async def upsert(self, data: Dict) -> T:
        """単一レコードの upsert インターフェース（未実装）.

        サブクラスでオーバーライドして実装してください。
        """
        raise NotImplementedError(
            "upsert is not implemented for this repository"
        )

    async def get(self, record_id: int) -> Optional[T]:
        """ID による単一レコード取得.

        Args:
            record_id (int): レコードの ID

        Returns:
            Optional[T]: 見つかればモデルインスタンス、存在しなければ None
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[T]:
        """ページネーション対応で複数レコードを取得する.

        Args:
            skip (int): 取得開始オフセット（デフォルト: 0）
            limit (int): 取得件数（デフォルト: 100）

        Returns:
            List[T]: モデルインスタンスのリスト
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
        """レコードを更新して更新後のインスタンスを返す.

        Args:
            record_id (int): 更新対象のレコード ID
            data (Dict): 更新フィールドの辞書

        Returns:
            Optional[T]: 更新後のモデルインスタンス、存在しない場合は None

        Raises:
            SQLAlchemyError: DB 操作中の例外が発生する可能性があります

        Notes:
            トランザクションのコミットは Service 層で行ってください。
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
        """指定 ID のレコードを削除する.

        Args:
            record_id (int): 削除対象のレコード ID

        Returns:
            bool: 削除に成功したら True、存在しなければ False

        Raises:
            SQLAlchemyError: DB 操作中の例外が発生する可能性があります

        Notes:
            トランザクションのコミットは Service 層で行ってください。
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
        """複数レコードを一括作成する.

        Args:
            records (List[dict]): レコード辞書のリスト

        Returns:
            List[T]: 作成されたモデルインスタンスのリスト

        Raises:
            SQLAlchemyError: DB 操作中の例外が発生する可能性があります

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        instances = [self.model(**record) for record in records]
        return await self._add_all_and_flush(instances)

    async def count(self) -> int:
        """モデルテーブルの総件数を返す.

        Returns:
            int: テーブル内の総件数
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        stmt = select(sql_count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def exists(self, record_id: int) -> bool:
        """指定 ID のレコードが存在するかを判定する.

        Args:
            record_id (int): 確認するレコード ID

        Returns:
            bool: 存在する場合は True
        """
        if self.model is None:
            raise ValueError("Repository model is not set")

        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none() is not None
