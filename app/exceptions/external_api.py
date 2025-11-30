"""
例外処理モジュール - 外部API関連例外

外部APIとの通信に関連する例外クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from app.exceptions.base import AppException


class ExternalAPIError(AppException):
    """外部API呼び出しの基底例外クラス"""

    default_message = "External API request failed"
    default_error_code = "EXTERNAL_API_ERROR"
    default_status_code = 502


class YahooFinanceError(ExternalAPIError):
    """Yahoo Finance API エラー"""

    default_message = "Yahoo Finance API request failed"
    default_error_code = "YAHOO_FINANCE_ERROR"
    default_status_code = 502


class JPXAPIError(ExternalAPIError):
    """JPX API エラー"""

    default_message = "JPX API request failed"
    default_error_code = "JPX_API_ERROR"
    default_status_code = 502


class APITimeoutError(ExternalAPIError):
    """API タイムアウトエラー"""

    default_message = "API request timeout"
    default_error_code = "API_TIMEOUT"
    default_status_code = 504


class APIRateLimitError(ExternalAPIError):
    """APIレート制限超過エラー"""

    default_message = "API rate limit exceeded"
    default_error_code = "API_RATE_LIMIT"
    default_status_code = 429
