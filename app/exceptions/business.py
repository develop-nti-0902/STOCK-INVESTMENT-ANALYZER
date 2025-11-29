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
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            context=context,
        )


class InsufficientDataError(BusinessError):
    """データ不足エラー"""

    def __init__(
        self,
        *,
        message: str = "Insufficient data for processing",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_DATA",
            status_code=422,
            context=context,
        )


class CalculationError(BusinessError):
    """計算処理エラー"""

    def __init__(
        self,
        *,
        message: str = "Calculation error occurred",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="CALCULATION_ERROR",
            status_code=500,
            context=context,
        )
