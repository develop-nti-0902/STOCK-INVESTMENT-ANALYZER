"""
例外処理モジュール - バリデーション関連例外

入力値検証に関連する例外クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from typing import Optional

from app.exceptions.base import AppException


class ValidationError(AppException):
    """バリデーションエラーの基底例外クラス"""

    def __init__(
        self,
        *,
        message: str = "Validation failed",
        error_code: str = "VALIDATION_ERROR",
        status_code: int = 400,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            original_error=original_error,
        )


class SchemaValidationError(ValidationError):
    """Pydanticスキーマ検証エラー"""

    def __init__(
        self,
        *,
        message: str = "Schema validation failed",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="SCHEMA_VALIDATION_ERROR",
            status_code=400,
            details=details,
            original_error=original_error,
        )


class FieldValidationError(ValidationError):
    """特定フィールドの検証エラー"""

    def __init__(
        self,
        *,
        message: str = "Field validation failed",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="FIELD_VALIDATION_ERROR",
            status_code=400,
            details=details,
            original_error=original_error,
        )
