"""
例外処理モジュールのテスト - ハンドラ
"""

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
    """軽量なモックRequestを生成する（クラス定義を避けてpylint対応）。"""
    url = SimpleNamespace(path=path)
    ns = SimpleNamespace(url=url, method=method)
    if app is not None:
        ns.app = app
    return ns


class TestGenerateRequestId:
    """generate_request_id()関数のテスト"""

    def test_generates_request_id(self):
        """
        リクエストIDを生成できることを確認
        """
        # Arrange: (特になし)

        # Act: リクエストIDを生成
        request_id = generate_request_id()

        # Assert: 正しい形式で生成されていることを確認
        assert request_id.startswith("req-")
        assert len(request_id) > 10

    def test_generates_unique_ids(self):
        """
        異なるIDが生成されることを確認
        """
        # Arrange: (特になし)

        # Act: 2つのリクエストIDを生成
        id1 = generate_request_id()
        id2 = generate_request_id()

        # Assert: 異なるIDが生成されることを確認
        assert id1 != id2


class TestCreateErrorResponse:
    """create_error_response()関数のテスト"""

    def test_creates_basic_error_response(self):
        """
        基本的なエラーレスポンスを生成
        """
        # Arrange: (特になし)

        # Act: 基本的なエラーレスポンスを生成
        response = create_error_response(
            error_code="TEST_ERROR",
            message="Test error message",
        )

        # Assert: レスポンスの構造が正しいことを確認
        assert response["error"] == "TEST_ERROR"
        assert response["message"] == "Test error message"
        assert response["details"] == {}
        assert "meta" in response
        assert "timestamp" in response["meta"]
        assert "request_id" in response["meta"]

    def test_creates_error_response_with_details(self):
        """
        詳細情報を含むエラーレスポンスを生成
        """
        # Arrange: (特になし)

        # Act: 詳細情報を含むエラーレスポンスを生成
        response = create_error_response(
            error_code="VALIDATION_ERROR",
            message="Validation failed",
            details={"field": "symbol", "value": "invalid"},
        )

        # Assert: 詳細情報が正しく含まれていることを確認
        assert response["details"]["field"] == "symbol"
        assert response["details"]["value"] == "invalid"

    def test_creates_error_response_with_request_id(self):
        """
        リクエストIDを指定してエラーレスポンスを生成
        """
        # Arrange: (特になし)

        # Act: リクエストIDを指定してエラーレスポンスを生成
        response = create_error_response(
            error_code="TEST_ERROR",
            message="Test message",
            request_id="test-req-123",
        )

        # Assert: 指定したリクエストIDが設定されていることを確認
        assert response["meta"]["request_id"] == "test-req-123"


@pytest.mark.asyncio
class TestAppExceptionHandler:
    """app_exception_handler()関数のテスト"""

    async def test_handles_app_exception(self):
        """AppExceptionを処理できることを確認"""

        # Arrange: モックリクエストとAppExceptionを準備
        request = create_mock_request("/test", "GET")

        exc = AppException(
            message="Test app exception",
            error_code="APP_ERROR",
            status_code=400,
            context={"details": {"key": "value"}},
        )

        # Act: ハンドラーを呼び出し
        response = await app_exception_handler(request, exc)

        # Assert: 正しいレスポンスが返されることを確認
        assert response.status_code == 400
        body = response.body.decode()
        assert "APP_ERROR" in body
        assert "Test app exception" in body

    def helper_noop(self):
        """pylint対策用の補助メソッド。"""
        return None


@pytest.mark.asyncio
class TestHttpExceptionHandler:
    """http_exception_handler()関数のテスト"""

    async def test_handles_http_exception(self):
        """HTTPExceptionを処理できることを確認"""

        # Arrange: モックリクエストとHTTPExceptionを準備
        request = create_mock_request("/test", "GET")

        exc = HTTPException(
            status_code=404,
            detail="Not found",
        )

        # Act: ハンドラーを呼び出し
        response = await http_exception_handler(request, exc)

        # Assert: 正しいレスポンスが返されることを確認
        assert response.status_code == 404
        body = response.body.decode()
        assert "Not found" in body

    def helper_noop(self):
        """pylint対策用の補助メソッド。"""
        return None


@pytest.mark.asyncio
class TestGeneralExceptionHandler:
    """general_exception_handler()関数のテスト"""

    async def test_handles_general_exception(self):
        """
        一般的な例外を処理できることを確認
        """

        # Arrange: モックリクエストと一般例外を準備
        request = create_mock_request("/test", "GET")

        exc = ValueError("Unexpected error")

        # Act: ハンドラーを呼び出し
        response = await general_exception_handler(request, exc)

        # Assert: 正しいレスポンスが返されることを確認
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body

    async def test_handles_general_exception_with_debug_mode(self):
        """
        DEBUG=Trueの場合、トレースバックが含まれることを確認
        """

        # Arrange: DEBUGモード有効なモックリクエストを準備（SimpleNamespaceで軽量生成）
        settings_ns = SimpleNamespace(DEBUG=True)
        app_ns = SimpleNamespace(state=SimpleNamespace(settings=settings_ns))
        request = create_mock_request("/test", "GET", app=app_ns)
        exc = ValueError("Test error with debug")

        # Act: ハンドラーを呼び出し
        response = await general_exception_handler(request, exc)

        # Assert: トレースバックが含まれていることを確認
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
        assert "traceback" in body
        assert "Test error with debug" in body

    async def test_handles_general_exception_without_debug_mode(self):
        """
        DEBUG=Falseの場合、詳細なエラー情報が隠されることを確認
        """

        # Arrange: DEBUGモード無効なモックリクエストを準備（SimpleNamespaceで軽量生成）
        settings_ns = SimpleNamespace(DEBUG=False)
        app_ns = SimpleNamespace(state=SimpleNamespace(settings=settings_ns))
        request = create_mock_request("/test", "GET", app=app_ns)
        exc = ValueError("Sensitive error info")

        # Act: ハンドラーを呼び出し
        response = await general_exception_handler(request, exc)

        # Assert: 詳細情報が隠されていることを確認
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
        assert "An unexpected error occurred" in body
        assert "Sensitive error info" not in body


@pytest.mark.asyncio
class TestValidationExceptionHandler:
    """validation_exception_handler()関数のテスト"""

    async def test_handles_validation_exception(self):
        """
        RequestValidationErrorを処理できることを確認
        """

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
        """
        RequestValidationError以外の例外を処理できることを確認
        """

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
    """http_exception_handler()関数の追加テスト"""

    async def test_handles_http_exception_with_dict_detail(self):
        """
        HTTPException.detailが辞書形式の場合を確認
        """

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
        """
        HTTPException以外の例外を処理できることを確認
        """

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
    """app_exception_handler()関数の追加テスト"""

    async def test_handles_app_exception_with_original_error(self):
        """
        original_errorがある場合のログ出力を確認
        """

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
        """
        AppException以外の例外を処理できることを確認
        """

        # Arrange: モックリクエストと一般例外を準備
        request = create_mock_request("/test", "GET")
        exc = ValueError("Not an app exception")

        # Act: ハンドラーを呼び出し
        response = await app_exception_handler(request, exc)

        # Assert: INTERNAL_SERVER_ERRORが返されることを確認
        assert response.status_code == 500
        body = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in body
