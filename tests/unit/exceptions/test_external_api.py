"""Tests for external API-related exception classes."""

from app.exceptions.base import AppException
from app.exceptions.external_api import (
    APIRateLimitError,
    APITimeoutError,
    ExternalAPIError,
    JPXAPIError,
    YahooFinanceError,
)


class TestExternalAPIErrors:
    """Tests for External API exception subclasses and defaults."""

    def test_external_api_error_defaults(self):
        """Verify ExternalAPIError default attributes."""
        exc = ExternalAPIError()
        assert isinstance(exc, AppException)
        assert exc.message == "External API request failed"
        assert exc.error_code == "EXTERNAL_API_ERROR"
        assert exc.status_code == 502

    def test_yahoo_finance_error_defaults(self):
        """Verify YahooFinanceError inherits ExternalAPIError."""
        exc = YahooFinanceError()
        assert isinstance(exc, ExternalAPIError)
        assert exc.error_code == "YAHOO_FINANCE_ERROR"

    def test_jpx_api_error_defaults(self):
        """Verify JPXAPIError inherits ExternalAPIError."""
        exc = JPXAPIError()
        assert isinstance(exc, ExternalAPIError)
        assert exc.error_code == "JPX_API_ERROR"

    def test_api_timeout_and_rate_limit_defaults(self):
        """Verify default HTTP status codes for timeout and rate limit errors."""
        assert APITimeoutError().status_code == 504
        assert APIRateLimitError().status_code == 429
