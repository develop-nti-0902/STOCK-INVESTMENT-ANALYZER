"""
例外処理モジュール - 外部API関連例外

外部APIとの通信に関連する例外クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from typing import Optional

from app.exceptions.base import AppException


class ExternalAPIError(AppException):
    """外部API呼び出しの基底例外クラス"""

    def __init__(
        self,
        *,
        message: str = "External API request failed",
        error_code: str = "EXTERNAL_API_ERROR",
        status_code: int = 502,
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


class YahooFinanceError(ExternalAPIError):
    """Yahoo Finance API エラー"""

    def __init__(
        self,
        *,
        message: str = "Yahoo Finance API request failed",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="YAHOO_FINANCE_ERROR",
            status_code=502,
            details=details,
            original_error=original_error,
        )


class JPXAPIError(ExternalAPIError):
    """JPX API エラー"""

    def __init__(
        self,
        *,
        message: str = "JPX API request failed",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="JPX_API_ERROR",
            status_code=502,
            details=details,
            original_error=original_error,
        )


class APITimeoutError(ExternalAPIError):
    """API タイムアウトエラー"""

    def __init__(
        self,
        *,
        message: str = "API request timeout",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="API_TIMEOUT",
            status_code=504,
            details=details,
            original_error=original_error,
        )


class APIRateLimitError(ExternalAPIError):
    """APIレート制限超過エラー"""

    def __init__(
        self,
        *,
        message: str = "API rate limit exceeded",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="API_RATE_LIMIT",
            status_code=429,
            details=details,
            original_error=original_error,
        )
