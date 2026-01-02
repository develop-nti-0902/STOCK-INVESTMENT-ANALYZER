"""データ変換抽象基底クラス.

外部データ形式と内部データ形式の相互変換を抽象化します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

# ジェネリック型パラメータ: 変換するデータ型
T = TypeVar("T")


class BaseConverter(ABC, Generic[T]):
    """データ変換の抽象基底クラス.

    全ての Converter はこのクラスを継承し、外部形式と内部形式の相互変換を実装します.

    Type Parameters:
        T: 内部データの型（Pydantic モデルなど）
    """

    @abstractmethod
    def to_pydantic(self, data: Any) -> T:
        """
        外部形式 → Pydanticモデル変換（サブクラスで実装）

        Args:
            data: 変換元データ（dict, DataFrame行など）

        Returns:
            T: Pydanticモデル

        Raises:
            ValueError: データ形式が不正な場合
        """

    @abstractmethod
    def from_pydantic(self, model: T) -> dict[str, Any]:
        """
        Pydanticモデル → 辞書変換（サブクラスで実装）

        Args:
            model: Pydanticモデル

        Returns:
            dict[str, Any]: 辞書形式データ

        Raises:
            ValueError: モデルが不正な場合
        """

    def to_pydantic_batch(self, data_list: list[Any]) -> list[T]:
        """
        外部形式リスト → Pydanticモデルリスト変換（デフォルト実装）

        Args:
            data_list: 変換元データのリスト

        Returns:
            list[T]: Pydanticモデルのリスト
        """
        return [self.to_pydantic(data) for data in data_list]

    def from_pydantic_batch(self, model_list: list[T]) -> list[dict[str, Any]]:
        """
        Pydanticモデルリスト → 辞書リスト変換（デフォルト実装）

        Args:
            model_list: Pydanticモデルのリスト

        Returns:
            list[dict[str, Any]]: 辞書形式データのリスト
        """
        return [self.from_pydantic(model) for model in model_list]

    def to_dataframe(self, data: list[T]) -> Any:
        """
        Pydanticモデルリスト → DataFrame変換（オプション）

        Args:
            data: Pydanticモデルのリスト

        Returns:
            Any: pandas DataFrame（pandasがインストールされている場合）

        Raises:
            NotImplementedError: pandasがインストールされていない場合

        Note:
            pandas依存を避けるため、デフォルトではNotImplementedError。
            必要に応じてサブクラスでオーバーライドしてください。
        """
        raise NotImplementedError(
            "to_dataframe requires pandas. Override in subclass if needed."
        )

    @abstractmethod
    def from_dataframe(self, df: Any, *args, **kwargs) -> list[T]:
        """
        DataFrame → Pydanticモデルリスト変換（サブクラスで実装）

        Args:
            df: pandas DataFrame
            *args: 追加の位置引数（サブクラス依存）
            **kwargs: 追加のキーワード引数（サブクラス依存）

        Returns:
            list[T]: Pydanticモデルのリスト

        Raises:
            NotImplementedError: pandasがインストールされていない場合

        Note:
            pandas依存を避けるため、デフォルトではNotImplementedError。
            必要に応じてサブクラスでオーバーライドしてください。
        """
        raise NotImplementedError(
            "from_dataframe requires pandas. "
            "Override in subclass if needed."
        )
