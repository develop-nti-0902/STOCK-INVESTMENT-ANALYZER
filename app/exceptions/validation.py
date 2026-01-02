"""例外処理モジュール - バリデーション関連例外.

入力値検証に関連する例外クラスを定義します。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from app.exceptions.base import AppException


class ValidationError(AppException):
    """バリデーションエラーの基底例外クラス.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Validation failed"
    default_error_code = "VALIDATION_ERROR"
    default_status_code = 400


class SchemaValidationError(ValidationError):
    """Pydanticスキーマ検証エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Schema validation failed"
    default_error_code = "SCHEMA_VALIDATION_ERROR"
    default_status_code = 400


class FieldValidationError(ValidationError):
    """特定フィールドの検証エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Field validation failed"
    default_error_code = "FIELD_VALIDATION_ERROR"
    default_status_code = 400
