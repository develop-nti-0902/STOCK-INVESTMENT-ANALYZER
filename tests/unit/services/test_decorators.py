"""
デコレータ（error_handler、retry）の単体テスト
"""

import pytest

from app.exceptions import ServiceError
from app.services.core.decorators import handle_service_error, retry_on_error


class TestHandleServiceError:
    """handle_service_errorデコレータのテスト"""

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """非同期関数の正常動作テスト"""

        @handle_service_error(error_message="Test failed")
        async def async_func(value: int) -> int:
            return value * 2

        result = await async_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_async_function_with_error(self):
        """非同期関数でのエラーハンドリングテスト"""

        @handle_service_error(
            error_message="Test failed", error_code="TEST_ERROR"
        )
        async def async_func_with_error():
            raise ValueError("Original error")

        with pytest.raises(ServiceError) as exc_info:
            await async_func_with_error()

        assert "Test failed" in str(exc_info.value)
        assert exc_info.value.error_code == "TEST_ERROR"

    def test_sync_function_success(self):
        """同期関数の正常動作テスト"""

        @handle_service_error(error_message="Test failed")
        def sync_func(value: int) -> int:
            return value * 2

        result = sync_func(5)
        assert result == 10

    def test_sync_function_with_error(self):
        """同期関数でのエラーハンドリングテスト"""

        @handle_service_error(
            error_message="Test failed", error_code="TEST_ERROR"
        )
        def sync_func_with_error():
            raise ValueError("Original error")

        with pytest.raises(ServiceError) as exc_info:
            sync_func_with_error()

        assert "Test failed" in str(exc_info.value)
        assert exc_info.value.error_code == "TEST_ERROR"

    @pytest.mark.asyncio
    async def test_service_error_passthrough(self):
        """ServiceErrorはそのまま再送出されることを確認"""

        @handle_service_error(error_message="Test failed")
        async def async_func_with_service_error():
            raise ServiceError(message="Direct service error")

        with pytest.raises(ServiceError) as exc_info:
            await async_func_with_service_error()

        assert "Direct service error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reraise_false(self):
        """reraise=Falseの場合、例外を再送出せずNoneを返す"""

        @handle_service_error(error_message="Test failed", reraise=False)
        async def async_func_with_error():
            raise ValueError("Original error")

        result = await async_func_with_error()
        assert result is None


class TestRetryOnError:
    """retry_on_errorデコレータのテスト"""

    @pytest.mark.asyncio
    async def test_async_function_success_first_try(self):
        """非同期関数が初回で成功する場合のテスト"""

        @retry_on_error(max_retries=3)
        async def async_func():
            return "success"

        result = await async_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_function_success_after_retry(self):
        """非同期関数がリトライ後に成功する場合のテスト"""
        attempt = {"count": 0}

        @retry_on_error(max_retries=3, delay=0.01)
        async def async_func_with_retry():
            attempt["count"] += 1
            if attempt["count"] < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await async_func_with_retry()
        assert result == "success"
        assert attempt["count"] == 3

    @pytest.mark.asyncio
    async def test_async_function_all_retries_failed(self):
        """非同期関数が全てのリトライに失敗する場合のテスト"""

        @retry_on_error(max_retries=2, delay=0.01)
        async def async_func_always_fail():
            raise ValueError("Permanent error")

        with pytest.raises(ValueError, match="Permanent error"):
            await async_func_always_fail()

    def test_sync_function_success_first_try(self):
        """同期関数が初回で成功する場合のテスト"""

        @retry_on_error(max_retries=3)
        def sync_func():
            return "success"

        result = sync_func()
        assert result == "success"

    def test_sync_function_success_after_retry(self):
        """同期関数がリトライ後に成功する場合のテスト"""
        attempt = {"count": 0}

        @retry_on_error(max_retries=3, delay=0.01)
        def sync_func_with_retry():
            attempt["count"] += 1
            if attempt["count"] < 3:
                raise ValueError("Temporary error")
            return "success"

        result = sync_func_with_retry()
        assert result == "success"
        assert attempt["count"] == 3

    def test_sync_function_all_retries_failed(self):
        """同期関数が全てのリトライに失敗する場合のテスト"""

        @retry_on_error(max_retries=2, delay=0.01)
        def sync_func_always_fail():
            raise ValueError("Permanent error")

        with pytest.raises(ValueError, match="Permanent error"):
            sync_func_always_fail()

    @pytest.mark.asyncio
    async def test_specific_exceptions_only(self):
        """特定の例外のみをリトライ対象とするテスト"""

        @retry_on_error(max_retries=2, delay=0.01, exceptions=(ValueError,))
        async def async_func_with_specific_error():
            raise TypeError("This should not be retried")

        # TypeErrorはリトライされずに即座に送出される
        with pytest.raises(TypeError, match="This should not be retried"):
            await async_func_with_specific_error()

    @pytest.mark.asyncio
    async def test_backoff_strategy(self):
        """指数バックオフ戦略のテスト"""
        attempt = {"count": 0}

        @retry_on_error(max_retries=3, delay=0.01, backoff=2.0)
        async def async_func_with_backoff():
            attempt["count"] += 1
            raise ValueError("Error")

        with pytest.raises(ValueError):
            await async_func_with_backoff()

        # 3回リトライした（初回 + 3回リトライ = 4回実行）
        assert attempt["count"] == 4
