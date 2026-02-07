"""例外処理モジュールのテスト - validation.py."""

from app.exceptions.base import AppException
from app.exceptions.validation import FieldValidationError, SchemaValidationError, ValidationError


class TestValidationErrors:
    """`ValidationError` 系例外のデフォルト値を検証します."""

    def test_validation_error_defaults(self):
        """`ValidationError` の標準プロパティを検証します."""
        exc = ValidationError()
        assert isinstance(exc, AppException)
        assert exc.message == "Validation failed"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.status_code == 400

    def test_schema_validation_error_defaults(self):
        """`SchemaValidationError` のエラーコードを検証します."""
        exc = SchemaValidationError()
        assert isinstance(exc, ValidationError)
        assert exc.error_code == "SCHEMA_VALIDATION_ERROR"

    def test_field_validation_error_defaults(self):
        """`FieldValidationError` のエラーコードを検証します."""
        exc = FieldValidationError()
        assert isinstance(exc, ValidationError)
        assert exc.error_code == "FIELD_VALIDATION_ERROR"
