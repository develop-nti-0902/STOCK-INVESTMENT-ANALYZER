"""データ保存抽象基底クラス.

データベースへの保存ロジックを抽象化する基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# ジェネリック型パラメータ: 保存するデータ型
T = TypeVar("T")


class BaseSaver(ABC, Generic[T]):
    """データ保存の抽象基底クラス（Strategy パターン）.

    非同期処理を前提に単一保存・バルク保存のインターフェースを定義します.

    Type Parameters:
        T: 保存対象のデータ型（Pydantic モデル等）
    """

    @abstractmethod
    async def save(self, data: T, **kwargs: Any) -> Any:
        """
        単一データ保存（サブクラスで実装）.

        Args:
            data: 保存するデータ（Pydanticモデルなど）
            **kwargs: 追加パラメータ（upsert, conflict_actionなど）

        Returns:
            bool: 保存が成功した場合True

        Raises:
            ValueError: データが不正な場合
            RuntimeError: 保存処理に失敗した場合
        """

    @abstractmethod
    async def save_batch(self, data_list: list[T], **kwargs: Any) -> Any:
        """
        複数データ一括保存（サブクラスで実装）.

        Args:
            data_list: 保存するデータのリスト
            **kwargs: 追加パラメータ

        Returns:
            int: 保存に成功したレコード数

        Raises:
            ValueError: データリストが不正な場合
            RuntimeError: 保存処理に失敗した場合

        Note:
            バッチ保存はトランザクション内で実行することを推奨します。
            部分的な成功を許容する場合は、戻り値で成功数を返してください。
        """

    def validate_data_sync(self, data: T) -> bool:
        """データの同期検証（サブクラスで上書き可）.

        サブクラスが同期的な検証ロジックを提供する場合はこのメソッドを
        オーバーライドしてください。非同期環境からは `validate_data`(async)
        経由で呼ばれ、内部でこの同期メソッドを利用します。

        Args:
            data: 検証対象のデータ

        Returns:
            bool: データが有効な場合 True.
        """
        if data is None:
            return False
        return True

    async def validate_data(self, data: T) -> bool:
        """非同期検証エントリポイント.

        デフォルト実装は `validate_data_sync` を呼び出します。サブクラスが
        非同期検証を直接提供する場合はこのメソッドをオーバーライドしてください.
        """
        res = self.validate_data_sync(data)
        if asyncio.iscoroutine(res):
            return await res
        return res

    async def prepare_for_save(self, data: T) -> dict[str, Any]:
        """
        保存前のデータ準備（オプション、サブクラスでオーバーライド可能）.

        Args:
            data: 準備するデータ

        Returns:
            dict[str, Any]: DB保存用の辞書形式データ

        Note:
            Pydanticモデル → SQLAlchemyモデル変換などに使用します。
        """
        if hasattr(data, "model_dump"):
            # Pydantic v2
            return data.model_dump()
        if hasattr(data, "dict"):
            # Pydantic v1
            return data.dict()
        return {}

    async def handle_save_error(self, data: T, error: Exception) -> None:
        """
        保存エラーのハンドリング（オプション、サブクラスでオーバーライド可能）.

        Args:
            data: エラーが発生したデータ
            error: 発生した例外

        Note:
            デフォルトではログ出力のみ。サブクラスで独自のエラー処理を実装可能。
        """
        # ロガー統合時にログ出力を追加予定
