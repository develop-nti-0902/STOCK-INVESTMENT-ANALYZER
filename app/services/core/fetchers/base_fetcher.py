"""
データ取得抽象基底クラス

外部APIやデータソースからのデータ取得を抽象化します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# ジェネリック型パラメータ: 取得するデータ型
T = TypeVar("T")


class BaseFetcher(ABC, Generic[T]):
    """
    データ取得の抽象基底クラス（Strategy パターン）

    全てのFetcherはこのクラスを継承し、fetch/fetch_batchメソッドを実装します。
    非同期処理を前提とした設計で、大量データの並列取得に対応します。

    Type Parameters:
        T: 取得するデータの型（Pydanticモデルなど）

    Examples:
        >>> class StockPriceFetcher(BaseFetcher[StockData]):
        ...     async def fetch(self, identifier: str, **kwargs) -> StockData:
        ...         # Yahoo Finance APIから取得
        ...         return stock_data
        ...
        ...     async def fetch_batch(
        ...         self, identifiers: list[str], **kwargs
        ...     ) -> list[StockData]:
        ...         # 複数銘柄を一括取得
        ...         return stock_data_list
    """

    @abstractmethod
    async def fetch(self, identifier: str, **kwargs: Any) -> T:
        """
        単一データ取得（サブクラスで実装）

        Args:
            identifier: データを識別する文字列（銘柄コード、URLなど）
            **kwargs: 追加パラメータ（interval, period, etc.）

        Returns:
            T: 取得したデータ（Pydanticモデルなど）

        Raises:
            ValueError: 識別子が不正な場合
            RuntimeError: データ取得に失敗した場合
        """

    @abstractmethod
    async def fetch_batch(
        self, identifiers: list[str], **kwargs: Any
    ) -> list[T]:
        """
        複数データ一括取得（サブクラスで実装）

        Args:
            identifiers: データ識別子のリスト
            **kwargs: 追加パラメータ

        Returns:
            list[T]: 取得したデータのリスト

        Raises:
            ValueError: 識別子リストが不正な場合
            RuntimeError: データ取得に失敗した場合

        Note:
            個別のエラーは記録し、取得可能なデータのみ返すことも可能です。
            完全失敗時のみ例外を発生させることを推奨します。
        """

    async def validate_identifier(self, identifier: str) -> bool:
        """
        識別子の検証（オプション、サブクラスでオーバーライド可能）

        Args:
            identifier: 検証対象の識別子

        Returns:
            bool: 識別子が有効な場合True
        """
        if not identifier or not isinstance(identifier, str):
            return False
        return True

    async def handle_fetch_error(
        self, identifier: str, error: Exception
    ) -> None:
        """
        取得エラーのハンドリング（オプション、サブクラスでオーバーライド可能）

        Args:
            identifier: エラーが発生した識別子
            error: 発生した例外

        Note:
            デフォルトではログ出力のみ。サブクラスで独自のエラー処理を実装可能。
        """
        # ロガー統合時にログ出力を追加予定
