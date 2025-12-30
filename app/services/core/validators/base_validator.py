"""データ検証抽象基底クラス.

取得・保存前のデータ検証を抽象化する基底クラス群を提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from abc import ABC, abstractmethod
from typing import Any


class ValidationResult:
    """検証結果を保持するクラス.

    Attributes:
        is_valid (bool): 検証が成功したかどうか
        errors (list[str]): エラーメッセージ一覧
        warnings (list[str]): 警告メッセージ一覧
    """

    def __init__(
        self,
        is_valid: bool,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        """bool変換時にis_validを返す"""
        return self.is_valid

    def __repr__(self) -> str:
        return (
            f"ValidationResult(is_valid={self.is_valid}, "
            f"errors={self.errors}, warnings={self.warnings})"
        )


class BaseValidator(ABC):
    """データ検証の抽象基底クラス.

    Pydantic の型検証に加え、ビジネスルールに基づく検証を実装するために利用します。
    """

    @abstractmethod
    def validate(self, data: Any) -> ValidationResult:
        """
        単一データ検証（サブクラスで実装）

        Args:
            data: 検証対象のデータ

        Returns:
            ValidationResult: 検証結果

        Note:
            この検証はPydanticの型検証後に実行され、
            ビジネスロジック固有のルールをチェックします。
        """

    def validate_batch(self, data_list: list[Any]) -> list[ValidationResult]:
        """
        複数データ一括検証（デフォルト実装、オーバーライド可能）

        Args:
            data_list: 検証対象データのリスト

        Returns:
            list[ValidationResult]: 各データの検証結果リスト
        """
        return [self.validate(data) for data in data_list]

    def validate_required_fields(
        self, data: dict[str, Any], required_fields: list[str]
    ) -> bool:
        """
        必須フィールドの存在確認（ヘルパーメソッド）

        Args:
            data: 検証対象の辞書データ
            required_fields: 必須フィールド名のリスト

        Returns:
            bool: 全ての必須フィールドが存在する場合True
        """
        return all(
            field in data and data[field] is not None
            for field in required_fields
        )

    def validate_data_types(
        self, data: dict[str, Any], type_mapping: dict[str, type]
    ) -> bool:
        """
        データ型の検証（ヘルパーメソッド）

        Args:
            data: 検証対象の辞書データ
            type_mapping: フィールド名と期待する型のマッピング

        Returns:
            bool: 全てのフィールドが期待する型の場合True
        """
        for field, expected_type in type_mapping.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    return False
        return True

    def validate_range(
        self,
        value: float | int,
        min_value: float | int | None = None,
        max_value: float | int | None = None,
    ) -> bool:
        """
        数値範囲の検証（ヘルパーメソッド）

        Args:
            value: 検証対象の数値
            min_value: 最小値（Noneの場合は下限なし）
            max_value: 最大値（Noneの場合は上限なし）

        Returns:
            bool: 値が範囲内の場合True
        """
        if min_value is not None and value < min_value:
            return False
        if max_value is not None and value > max_value:
            return False
        return True
