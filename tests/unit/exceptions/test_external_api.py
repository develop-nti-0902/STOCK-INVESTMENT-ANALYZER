"""
例外処理モジュールのテスト - external_api.py
"""

from app.exceptions.base import AppException
from app.exceptions.external_api import (
    APIRateLimitError,
    APITimeoutError,
    ExternalAPIError,
    JPXAPIError,
    YahooFinanceError,
)


class TestExternalAPIErrors:
    def test_external_api_error_defaults(self):
        exc = ExternalAPIError()
        assert isinstance(exc, AppException)
        assert exc.message == "External API request failed"
        assert exc.error_code == "EXTERNAL_API_ERROR"
        assert exc.status_code == 502

    def test_yahoo_finance_error_defaults(self):
        exc = YahooFinanceError()
        assert isinstance(exc, ExternalAPIError)
        assert exc.error_code == "YAHOO_FINANCE_ERROR"

    def test_jpx_api_error_defaults(self):
        exc = JPXAPIError()
        assert isinstance(exc, ExternalAPIError)
        assert exc.error_code == "JPX_API_ERROR"

    def test_api_timeout_and_rate_limit_defaults(self):
        assert APITimeoutError().status_code == 504
        assert APIRateLimitError().status_code == 429
