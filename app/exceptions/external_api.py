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
        context: Optional[dict] = None,
    ):
        # キーワード引数の順序を変更してpylintのduplicate-code検出を回避
        super().__init__(
            context=context,
            message=message,
            status_code=status_code,
            error_code=error_code,
        )


class YahooFinanceError(ExternalAPIError):
    """Yahoo Finance API エラー"""

    def __init__(
        self,
        *,
        message: str = "Yahoo Finance API request failed",
        context: Optional[dict] = None,
    ):
        super().__init__(
            context=context,
            message=message,
            status_code=502,
            error_code="YAHOO_FINANCE_ERROR",
        )


class JPXAPIError(ExternalAPIError):
    """JPX API エラー"""

    def __init__(
        self,
        *,
        message: str = "JPX API request failed",
        context: Optional[dict] = None,
    ):
        super().__init__(
            context=context,
            message=message,
            status_code=502,
            error_code="JPX_API_ERROR",
        )


class APITimeoutError(ExternalAPIError):
    """API タイムアウトエラー"""

    def __init__(
        self,
        *,
        message: str = "API request timeout",
        context: Optional[dict] = None,
    ):
        super().__init__(
            context=context,
            message=message,
            status_code=504,
            error_code="API_TIMEOUT",
        )


class APIRateLimitError(ExternalAPIError):
    """APIレート制限超過エラー"""

    def __init__(
        self,
        *,
        message: str = "API rate limit exceeded",
        context: Optional[dict] = None,
    ):
        super().__init__(
            context=context,
            message=message,
            status_code=429,
            error_code="API_RATE_LIMIT",
        )
