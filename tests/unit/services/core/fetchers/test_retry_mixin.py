"""RetryMixinクラスの単体テスト."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.core.fetchers.retry_mixin import RetryMixin


class TestRetryMixin:
    """RetryMixinクラスのテスト."""

    @pytest.fixture
    def retry_mixin(self) -> RetryMixin:
        """テスト用のRetryMixinインスタンス."""
        with patch("app.services.core.fetchers.retry_mixin.get_settings") as mock_settings:
            mock_config = MagicMock()
            mock_config.YAHOO_FINANCE_MAX_RETRIES = 3
            mock_config.YAHOO_FINANCE_RETRY_BACKOFF = 2.0
            mock_settings.return_value = mock_config

            return RetryMixin()

    def test_init(self, retry_mixin: RetryMixin) -> None:
        """初期化テスト."""
        # Arrange - 準備

        # Act - 実行
        # Assert - 検証
        assert retry_mixin.max_retries == 3
        assert retry_mixin.backoff_factor == 2.0
        assert retry_mixin.retryable_exceptions == (
            ConnectionError,
            TimeoutError,
            OSError,
        )

    @pytest.mark.asyncio
    async def test_retry_success_first_attempt(self, retry_mixin: RetryMixin) -> None:
        """初回で成功する場合のテスト."""
        # Arrange - 準備
        mock_func = AsyncMock(return_value="success")

        # Act - 実行
        result = await retry_mixin._retry_async(mock_func, "test_operation")

        # Assert - 検証
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_success_after_retry(self, retry_mixin: RetryMixin) -> None:
        """リトライ後に成功する場合のテスト."""
        # Arrange - 準備
        mock_func = AsyncMock(side_effect=[ConnectionError("Failed"), "success"])

        # Act - 実行
        result = await retry_mixin._retry_async(mock_func, "test_operation")

        # Assert - 検証
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_max_attempts_exceeded(self, retry_mixin: RetryMixin) -> None:
        """最大リトライ回数を超える場合のテスト."""
        # Arrange - 準備
        mock_func = AsyncMock(side_effect=ConnectionError("Always fails"))

        # Act & Assert - 実行と検証
        with pytest.raises(ConnectionError):
            await retry_mixin._retry_async(mock_func, "test_operation")

        assert mock_func.call_count == 4  # 初回 + 3回リトライ

    @pytest.mark.asyncio
    async def test_retry_non_retryable_error(self, retry_mixin: RetryMixin) -> None:
        """リトライ不可エラーの場合のテスト."""
        # Arrange - 準備
        mock_func = AsyncMock(side_effect=ValueError("Invalid input"))

        # Act & Assert - 実行と検証
        with pytest.raises(ValueError):
            await retry_mixin._retry_async(mock_func, "test_operation")

        assert mock_func.call_count == 1  # リトライせず1回のみ

    def test_is_retryable_error_connection_error(self, retry_mixin: RetryMixin) -> None:
        """ConnectionErrorがリトライ可能であることをテスト."""
        # Arrange - 準備

        # Act & Assert - 実行と検証
        assert retry_mixin._is_retryable_error(ConnectionError("Connection failed"))

    def test_is_retryable_error_timeout_error(self, retry_mixin: RetryMixin) -> None:
        """TimeoutErrorがリトライ可能であることをテスト."""
        # Arrange - 準備

        # Act & Assert - 実行と検証
        assert retry_mixin._is_retryable_error(TimeoutError("Timeout"))

    def test_is_retryable_error_os_error(self, retry_mixin: RetryMixin) -> None:
        """OSErrorがリトライ可能であることをテスト."""
        # Arrange - 準備

        # Act & Assert - 実行と検証
        assert retry_mixin._is_retryable_error(OSError("Network error"))

    def test_is_retryable_error_value_error(self, retry_mixin: RetryMixin) -> None:
        """ValueErrorがリトライ不可であることをテスト."""
        # Arrange - 準備

        # Act & Assert - 実行と検証
        assert not retry_mixin._is_retryable_error(ValueError("Invalid value"))

    def test_is_retryable_error_with_status_code(self, retry_mixin: RetryMixin) -> None:
        """HTTPステータスコードによる判定テスト."""
        # Arrange - 準備

        # Act & Assert - 実行と検証
        # 5xxエラーはリトライ可能
        error_500 = MagicMock()
        error_500.status = 500
        assert retry_mixin._is_retryable_error(error_500)

        # 429 (Rate limit) はリトライ可能
        error_429 = MagicMock()
        error_429.status = 429
        assert retry_mixin._is_retryable_error(error_429)

        # 404 はリトライ不可
        error_404 = MagicMock()
        error_404.status = 404
        assert not retry_mixin._is_retryable_error(error_404)

    def test_is_retryable_error_with_message(self, retry_mixin: RetryMixin) -> None:
        """エラーメッセージによる判定テスト."""
        # Arrange - 準備

        # Act & Assert - 実行と検証
        assert retry_mixin._is_retryable_error(Exception("Connection timeout"))
        assert retry_mixin._is_retryable_error(Exception("Network is unreachable"))
        assert retry_mixin._is_retryable_error(Exception("Rate limit exceeded"))
        assert not retry_mixin._is_retryable_error(Exception("Invalid input data"))

    def test_calculate_delay(self, retry_mixin: RetryMixin) -> None:
        """遅延時間計算テスト."""
        # Arrange - 準備

        # Act - 実行
        delay1 = retry_mixin._calculate_delay(1)
        delay2 = retry_mixin._calculate_delay(2)
        delay3 = retry_mixin._calculate_delay(3)

        # Assert - 検証
        # バックオフ係数2.0なので、遅延時間が指数的に増加
        assert 0.75 <= delay1 <= 1.25  # 1.0 * jitter
        assert 1.5 <= delay2 <= 2.5  # 2.0 * jitter
        assert 3.0 <= delay3 <= 5.0  # 4.0 * jitter

        # 最大遅延時間を超えない
        assert delay1 <= 60.0
        assert delay2 <= 60.0
        assert delay3 <= 60.0

    def test_update_retry_config(self, retry_mixin: RetryMixin) -> None:
        """リトライ設定更新テスト."""
        # Arrange - 準備

        # Act - 実行
        retry_mixin.update_retry_config(max_retries=5, backoff_factor=1.5)

        # Assert - 検証
        assert retry_mixin.max_retries == 5
        assert retry_mixin.backoff_factor == 1.5

    def test_update_retry_config_partial(self, retry_mixin: RetryMixin) -> None:
        """部分的なリトライ設定更新テスト."""
        # Arrange - 準備
        original_backoff = retry_mixin.backoff_factor

        # Act - 実行
        retry_mixin.update_retry_config(max_retries=10)

        # Assert - 検証
        assert retry_mixin.max_retries == 10
        assert retry_mixin.backoff_factor == original_backoff

        retry_mixin.update_retry_config(backoff_factor=3.0)

        assert retry_mixin.max_retries == 10
        assert retry_mixin.backoff_factor == 3.0
