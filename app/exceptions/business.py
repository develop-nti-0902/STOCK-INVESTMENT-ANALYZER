"""例外処理モジュール - ビジネスロジック関連例外.

ビジネスルールに関連する例外クラスを定義します。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from app.exceptions.base import AppException


class BusinessError(AppException):
    """ビジネスロジックエラーの基底例外クラス.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Business logic error occurred"
    default_error_code = "BUSINESS_ERROR"
    default_status_code = 400


class ServiceError(BusinessError):
    """サービス層で発生する例外を表すクラス.

    補助として定義。サービス層のエラーハンドリングで一貫して利用します。
    """

    default_message = "Service error occurred"
    default_error_code = "SERVICE_ERROR"
    default_status_code = 500


class InsufficientDataError(BusinessError):
    """データ不足エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Insufficient data for processing"
    default_error_code = "INSUFFICIENT_DATA"
    default_status_code = 422


class CalculationError(BusinessError):
    """計算処理エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Calculation error occurred"
    default_error_code = "CALCULATION_ERROR"
    default_status_code = 500


class StockDataValidationError(BusinessError):
    """株価データ検証エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Stock data validation failed"
    default_error_code = "STOCK_DATA_VALIDATION_ERROR"
    default_status_code = 422


class DuplicateEmailError(BusinessError):
    """メールアドレスの重複エラー"""

    default_message = "Email already registered"
    default_error_code = "DUPLICATE_EMAIL"
    default_status_code = 409


class InvalidCredentialsError(BusinessError):
    """認証情報不正エラー"""

    default_message = "Invalid email or password"
    default_error_code = "INVALID_CREDENTIALS"
    default_status_code = 401
