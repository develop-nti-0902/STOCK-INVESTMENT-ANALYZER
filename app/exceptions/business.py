"""
例外処理モジュール - ビジネスロジック関連例外

ビジネスルールに関連する例外クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from app.exceptions.base import AppException


class BusinessError(AppException):
    """ビジネスロジックエラーの基底例外クラス"""

    default_message = "Business logic error occurred"
    default_error_code = "BUSINESS_ERROR"
    default_status_code = 400


class InsufficientDataError(BusinessError):
    """データ不足エラー"""

    default_message = "Insufficient data for processing"
    default_error_code = "INSUFFICIENT_DATA"
    default_status_code = 422


class CalculationError(BusinessError):
    """計算処理エラー"""

    default_message = "Calculation error occurred"
    default_error_code = "CALCULATION_ERROR"
    default_status_code = 500
