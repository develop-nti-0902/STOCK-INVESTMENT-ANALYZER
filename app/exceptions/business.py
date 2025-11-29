"""
例外処理モジュール - ビジネスロジック関連例外

ビジネスルールに関連する例外クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from typing import Optional

from app.exceptions.base import AppException


class BusinessError(AppException):
    """ビジネスロジックエラーの基底例外クラス"""

    def __init__(
        self,
        *,
        message: str = "Business logic error occurred",
        error_code: str = "BUSINESS_ERROR",
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


class InsufficientDataError(BusinessError):
    """データ不足エラー"""

    def __init__(
        self,
        *,
        message: str = "Insufficient data for processing",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_DATA",
            status_code=422,
            details=details,
            original_error=original_error,
        )


class CalculationError(BusinessError):
    """計算処理エラー"""

    def __init__(
        self,
        *,
        message: str = "Calculation error occurred",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="CALCULATION_ERROR",
            status_code=500,
            details=details,
            original_error=original_error,
        )
