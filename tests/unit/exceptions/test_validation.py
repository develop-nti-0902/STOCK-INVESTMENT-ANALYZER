"""
例外処理モジュールのテスト - validation.py
"""

from app.exceptions.base import AppException
from app.exceptions.validation import (
    FieldValidationError,
    SchemaValidationError,
    ValidationError,
)


class TestValidationErrors:
    def test_validation_error_defaults(self):
        exc = ValidationError()
        assert isinstance(exc, AppException)
        assert exc.message == "Validation failed"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 400

    def test_schema_validation_error_defaults(self):
        exc = SchemaValidationError()
        assert isinstance(exc, ValidationError)
        assert exc.error_code == "SCHEMA_VALIDATION_ERROR"

    def test_field_validation_error_defaults(self):
        exc = FieldValidationError()
        assert isinstance(exc, ValidationError)
        assert exc.error_code == "FIELD_VALIDATION_ERROR"
