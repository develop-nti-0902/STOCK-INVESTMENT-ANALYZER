"""Tests for exception handlers and error response utilities."""

from types import SimpleNamespace

import pytest
from fastapi.exceptions import HTTPException, RequestValidationError
from pydantic import BaseModel, ValidationError

from app.exceptions.base import AppException
from app.exceptions.handlers import (
    app_exception_handler,
    create_error_response,
    general_exception_handler,
    generate_request_id,
    http_exception_handler,
    validation_exception_handler,
)


def create_mock_request(path: str, method: str, app: object | None = None):
    """Create a lightweight mock Request object for tests."""
    url = SimpleNamespace(path=path)
    ns = SimpleNamespace(url=url, method=method)
    if app is not None:
        ns.app = app
    return ns


class TestGenerateRequestId:
    """Tests for `generate_request_id()` function."""

    def test_generates_request_id(self):
        """Generate a request id with expected prefix and length."""
        request_id = generate_request_id()
        assert request_id.startswith("req-")
        assert len(request_id) > 10

    def test_generates_unique_ids(self):
        """Generate unique request ids on subsequent calls."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        assert id1 != id2


class TestCreateErrorResponse:
    """Tests for `create_error_response()` utility."""

    def test_creates_basic_error_response(self):
        """Create a basic error response and validate its structure."""
        response = create_error_response(
            error_code="TEST_ERROR",
            message="Test error message",
        )
        assert response["error"]["code"] == "TEST_ERROR"
        assert response["error"]["message"] == "Test error message"
        assert response["error"]["details"] == {}
        assert "meta" in response
        assert "timestamp" in response["meta"]
        assert "request_id" in response["meta"]

    def test_creates_error_response_with_details(self):
        """Include details in the error response payload."""
        response = create_error_response(
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            details={"field": "symbol", "value": "invalid"},
        )
        assert response["error"]["details"]["field"] == "symbol"
        assert response["error"]["details"]["value"] == "invalid"

    def test_creates_error_response_with_request_id(self):
        """Use the provided request_id in the response meta."""
        response = create_error_response(
            error_code="TEST_ERROR",
            message="Test message",
            request_id="test-req-123",
        )
        assert response["meta"]["request_id"] == "test-req-123"


@pytest.mark.asyncio
class TestAppExceptionHandler:
    """Tests for `app_exception_handler()` behavior."""

    async def test_handles_app_exception(self):
        """Handle AppException and return proper HTTP response."""
        request = create_mock_request("/test", "GET")
        exc = AppException(
            message="Test app exception",
            error_code="APP_ERROR",
            status_code=400,
            context={"details": {"key": "value"}},
        )
        response = await app_exception_handler(request, exc)
        assert response.status_code == 400
        body = response.body.decode()
        assert "APP_ERROR" in body
        assert "Test app exception" in body

    def helper_noop(self):
        """No-op helper for pylint compatibility."""
        return None


@pytest.mark.asyncio
class TestHttpExceptionHandler:
    """Tests for `http_exception_handler()` behavior."""

    async def test_handles_http_exception(self):
        """Handle HTTPException and return its detail in response."""
        request = create_mock_request("/test", "GET")
        exc = HTTPException(
            status_code=404,
            detail="Not found",
        )
        response = await http_exception_handler(request, exc)
        assert response.status_code == 404
        body = response.body.decode()
        assert "Not found" in body

    def helper_noop(self):
        """No-op helper for pylint compatibility."""
        return None


@pytest.mark.asyncio
class TestGeneralExceptionHandler:
    """Tests for `general_exception_handler()` behavior."""

    async def test_handles_general_exception(self):
        """Handle a generic exception and return 500 response."""
        request = create_mock_request("/test", "GET")
        exc = ValueError("Unexpected error")
        response = await general_exception_handler(request, exc)
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body

    async def test_handles_general_exception_with_debug_mode(self):
        """Include traceback when DEBUG=True in app settings."""
        settings_ns = SimpleNamespace(DEBUG=True)
        app_ns = SimpleNamespace(state=SimpleNamespace(settings=settings_ns))
        request = create_mock_request("/test", "GET", app=app_ns)
        exc = ValueError("Test error with debug")
        response = await general_exception_handler(request, exc)
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
        assert "traceback" in body
        assert "Test error with debug" in body

    async def test_handles_general_exception_without_debug_mode(self):
        """Hide detailed error info when DEBUG=False in app settings."""
        settings_ns = SimpleNamespace(DEBUG=False)
        app_ns = SimpleNamespace(state=SimpleNamespace(settings=settings_ns))
        request = create_mock_request("/test", "GET", app=app_ns)
        exc = ValueError("Sensitive error info")
        response = await general_exception_handler(request, exc)
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
        assert "An unexpected error occurred" in body
        assert "Sensitive error info" not in body


@pytest.mark.asyncio
class TestValidationExceptionHandler:
    """Tests for `validation_exception_handler()`."""

    async def test_handles_validation_exception(self):
        """Handle RequestValidationError and return validation details."""
        # Arrange: モックリクエストとバリデーションエラーを準備
        request = create_mock_request("/test", "POST")

        # Pydantic v2のバリデーションエラーを作成
        class TestModel(BaseModel):
            name: str
            age: int

        validation_error: ValidationError | None = None
        try:
            # 型安全な方法でバリデーションエラーを発生させる
            TestModel.model_validate({"name": "test", "age": "invalid"})
        except ValidationError as ve:
            validation_error = ve

        # ValidationErrorが取得できていることを確認
        assert validation_error is not None
        exc = RequestValidationError(errors=validation_error.errors())

        # Act: ハンドラーを呼び出し
        response = await validation_exception_handler(request, exc)

        # Assert: 正しいレスポンスが返されることを確認
        assert response.status_code == 400
        body = response.body.decode()
        assert "VALIDATION_ERROR" in body
        assert "validation_errors" in body
        assert "age" in body

    async def test_handles_non_validation_exception(self):
        """Handle non-validation exceptions and return BAD_REQUEST."""
        # Arrange: モックリクエストと一般例外を準備
        request = create_mock_request("/test", "POST")
        exc = ValueError("Not a validation error")

        # Act: ハンドラーを呼び出し
        response = await validation_exception_handler(request, exc)

        # Assert: BAD_REQUESTが返されることを確認
        assert response.status_code == 400
        body = response.body.decode()
        assert "BAD_REQUEST" in body


@pytest.mark.asyncio
class TestHttpExceptionHandlerExtended:
    """Additional tests for `http_exception_handler()`."""

    async def test_handles_http_exception_with_dict_detail(self):
        """Handle HTTPException with dict detail and reflect fields in response."""
        # Arrange: dict形式のdetailを持つHTTPExceptionを準備
        request = create_mock_request("/test", "GET")

        exc = HTTPException(
            status_code=400,
            detail={
                "error": "CUSTOM_ERROR",
                "message": "Custom error message",
                "details": {"field": "value"},
            },
        )

        # Act: ハンドラーを呼び出し
        response = await http_exception_handler(request, exc)

        # Assert: 辞書の内容が正しく反映されることを確認
        assert response.status_code == 400
        body = response.body.decode()
        assert "CUSTOM_ERROR" in body
        assert "Custom error message" in body
        assert "field" in body

    async def test_handles_non_http_exception(self):
        """Handle non-HTTP exceptions and return INTERNAL_SERVER_ERROR."""
        # Arrange: モックリクエストと一般例外を準備
        request = create_mock_request("/test", "GET")
        exc = ValueError("Not an HTTP exception")

        # Act: ハンドラーを呼び出し
        response = await http_exception_handler(request, exc)

        # Assert: INTERNAL_SERVER_ERRORが返されることを確認
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body


@pytest.mark.asyncio
class TestAppExceptionHandlerExtended:
    """Additional tests for `app_exception_handler()`."""

    async def test_handles_app_exception_with_original_error(self):
        """Handle AppException with `original_error` and include wrapped message."""
        # Arrange: original_errorを持つAppExceptionを準備
        request = create_mock_request("/test", "GET")

        original = ValueError("Original error")
        exc = AppException(
            message="Wrapped exception",
            error_code="WRAPPED_ERROR",
            status_code=400,
            context={"original_error": original},
        )

        # Act: ハンドラーを呼び出し
        response = await app_exception_handler(request, exc)

        # Assert: 正しいレスポンスが返されることを確認
        assert response.status_code == 400
        body = response.body.decode()
        assert "WRAPPED_ERROR" in body
        assert "Wrapped exception" in body

    async def test_handles_non_app_exception(self):
        """Handle non-AppException and return INTERNAL_SERVER_ERROR."""
        # Arrange: モックリクエストと一般例外を準備
        request = create_mock_request("/test", "GET")
        exc = ValueError("Not an app exception")

        # Act: ハンドラーを呼び出し
        response = await app_exception_handler(request, exc)

        # Assert: INTERNAL_SERVER_ERRORが返されることを確認
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
