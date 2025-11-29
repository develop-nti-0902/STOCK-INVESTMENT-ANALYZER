"""
例外処理モジュールのテスト - 基底例外クラス
"""

from fastapi import HTTPException

from app.exceptions.base import AppException


class TestAppException:
    """AppException基底クラスのテスト"""

    def test_init_with_defaults(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でAppExceptionを初期化
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
        )

        # Assert: デフォルト値が正しく設定されていることを確認
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 500
        assert exc.details == {}
        assert exc.original_error is None

    def test_init_with_all_params(self):
        """
        全パラメータ指定での初期化
        """
        # Arrange: 元の例外を準備
        original = ValueError("Original error")

        # Act: 全パラメータを指定してAppExceptionを初期化
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"field": "test"},
            original_error=original,
        )

        # Assert: 全パラメータが正しく設定されていることを確認
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 400
        assert exc.details == {"field": "test"}
        assert exc.original_error is original

    def test_to_dict(self):
        """
        to_dict()メソッドのテスト
        """
        # Arrange: 詳細情報を持つAppExceptionを準備
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"field": "test", "value": "invalid"},
        )

        # Act: to_dict()を呼び出し
        result = exc.to_dict()

        # Assert: 辞書形式が正しいことを確認
        assert result == {
            "error": "TEST_ERROR",
            "message": "Test error",
            "details": {"field": "test", "value": "invalid"},
        }

    def test_to_http_exception(self):
        """
        to_http_exception()メソッドのテスト
        """
        # Arrange: AppExceptionを準備
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"field": "test"},
        )

        # Act: to_http_exception()を呼び出し
        http_exc = exc.to_http_exception()

        # Assert: HTTPExceptionに正しく変換されていることを確認
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 400
        assert http_exc.detail == {
            "error": "TEST_ERROR",
            "message": "Test error",
            "details": {"field": "test"},
        }

    def test_str_representation(self):
        """
        文字列表現のテスト
        """
        # Arrange: AppExceptionを準備
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
        )

        # Act & Assert: 文字列表現が正しいことを確認
        assert str(exc) == "[TEST_ERROR] Test error"

    def test_repr(self):
        """
        repr表現のテスト
        """
        # Arrange: AppExceptionを準備
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=400,
            details={"field": "test"},
        )

        # Act: repr()を呼び出し
        repr_str = repr(exc)

        # Assert: repr表現に必要な情報が含まれていることを確認
        assert "AppException" in repr_str
        assert "message='Test error'" in repr_str
        assert "error_code='TEST_ERROR'" in repr_str
        assert "status_code=400" in repr_str
        assert "details={'field': 'test'}" in repr_str

    def test_exception_inheritance(self):
        """
        Pythonの標準Exceptionを継承していることを確認
        """
        # Arrange & Act: AppExceptionを準備
        exc = AppException(
            message="Test error",
            error_code="TEST_ERROR",
        )

        # Assert: Exceptionクラスを継承していることを確認
        assert isinstance(exc, Exception)
        assert isinstance(exc, AppException)
