"""Tests for business-related exception classes."""

from app.exceptions.base import AppException
from app.exceptions.business import (
    BusinessError,
    CalculationError,
    InsufficientDataError,
    ServiceError,
    StockDataValidationError,
)


class TestBusinessErrors:
    """Tests for business exception classes and defaults."""

    def test_business_error_defaults(self):
        """Verify BusinessError default attributes."""
        exc = BusinessError()
        assert isinstance(exc, AppException)
        assert exc.message == "Business logic error occurred"
        assert exc.error_code == "BUSINESS_ERROR"
        assert exc.status_code == 400

    def test_service_error_inheritance_and_defaults(self):
        """Verify ServiceError inherits BusinessError and has expected defaults."""
        exc = ServiceError()
        assert isinstance(exc, BusinessError)
        assert exc.message == "Service error occurred"
        assert exc.error_code == "SERVICE_ERROR"
        assert exc.status_code == 500

    def test_insufficient_data_error_defaults(self):
        """Verify InsufficientDataError defaults."""
        exc = InsufficientDataError()
        assert isinstance(exc, BusinessError)
        assert exc.error_code == "INSUFFICIENT_DATA"
        assert exc.status_code == 422

    def test_calculation_error_defaults(self):
        """Verify CalculationError defaults."""
        exc = CalculationError()
        assert isinstance(exc, BusinessError)
        assert exc.error_code == "CALCULATION_ERROR"

    def test_stock_data_validation_error_defaults(self):
        """Verify StockDataValidationError defaults."""
        exc = StockDataValidationError()
        assert isinstance(exc, BusinessError)
        assert exc.error_code == "STOCK_DATA_VALIDATION_ERROR"
