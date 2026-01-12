"""リトライロジック Mixin クラス.

指数バックオフを用いたリトライ機能を提供し、リトライ可能エラーの判定や
最大リトライ回数の管理を行います。

仕様書: docs/architecture/layers/service_layer.md 3.1章
"""

import asyncio
import random
from typing import Any, Callable, Optional, TypeVar

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryMixin:
    """リトライロジックを提供する Mixin クラス.

    Attributes:
        max_retries (int): 最大リトライ回数
        backoff_factor (float): バックオフ係数
        retryable_exceptions (tuple[type, ...]): リトライ対象例外
    """

    def __init__(self) -> None:
        """RetryMixinを初期化します。"""
        config = get_settings()
        self.max_retries = config.YAHOO_FINANCE_MAX_RETRIES
        self.backoff_factor = config.YAHOO_FINANCE_RETRY_BACKOFF

        # リトライ可能な例外クラス
        self.retryable_exceptions = (
            ConnectionError,
            TimeoutError,
            OSError,  # ネットワーク関連のエラー
        )

    async def _retry_async(
        self,
        func: Callable[[], Any],
        operation_name: str,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        非同期関数をリトライ付きで実行します。

        Args:
            func: 実行する非同期関数
            operation_name: 操作名（ログ出力用）
            *args: funcに渡す位置引数
            **kwargs: funcに渡すキーワード引数

        Returns:
            Any: 関数の戻り値

        Raises:
            Exception: 最終的に失敗した場合の例外
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # リトライ前の待機
                    delay = self._calculate_delay(attempt)
                    logger.info(
                        "Retrying %s (attempt %d/%d) after %.2f seconds",
                        operation_name,
                        attempt + 1,
                        self.max_retries + 1,
                        delay,
                    )
                    await asyncio.sleep(delay)

                # 関数実行
                return await func(*args, **kwargs)

            except (ConnectionError, TimeoutError, OSError) as e:
                # リトライ可能なネットワーク関連エラーをキャッチ
                last_exception = self._handle_retry_exception(
                    e, attempt, operation_name
                )
                if last_exception is None:
                    continue
                raise last_exception from e

            except Exception as e:
                # 予期せぬ例外もキャッチして適切に処理
                # リトライロジックとして、外部API等の未知のエラーを処理するため
                last_exception = self._handle_retry_exception(
                    e, attempt, operation_name
                )
                if last_exception is None:
                    continue
                raise last_exception from e

        # ここには到達しないはずだが、念のため
        if last_exception:
            raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """
        リトライ間の遅延時間を計算します。

        Args:
            attempt: 現在のリトライ回数（1始まり）

        Returns:
            float: 待機時間（秒）
        """
        # 指数バックオフ: base_delay * (backoff_factor ^ (attempt - 1))
        # ジッターを追加して衝突を避ける
        base_delay = 1.0  # 基本遅延1秒
        exponential_delay = base_delay * (self.backoff_factor ** (attempt - 1))

        # ジッターを追加（±25%のランダム変動）
        jitter = random.uniform(0.75, 1.25)
        delay = exponential_delay * jitter

        # 最大遅延時間を制限（例: 60秒）
        max_delay = 60.0
        return min(delay, max_delay)

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        エラーがリトライ可能かどうかを判定します。

        Args:
            error: 判定対象の例外

        Returns:
            bool: リトライ可能な場合True
        """
        # 例外の型で判定
        if isinstance(error, self.retryable_exceptions):
            return True

        # HTTPステータスコードで判定（aiohttpの場合）
        if hasattr(error, "status"):
            status = getattr(error, "status", 0)
            # 5xxエラーや特定の4xxエラーはリトライ可能
            retryable_statuses = {
                408,
                429,
                500,
                502,
                503,
                504,
            }  # Timeout, Rate limit, Server errors
            if status in retryable_statuses:
                return True

        # 特定のエラーメッセージで判定
        error_msg = str(error).lower()
        retryable_patterns = [
            "connection",
            "timeout",
            "network",
            "temporary",
            "rate limit",
        ]

        return any(pattern in error_msg for pattern in retryable_patterns)

    def update_retry_config(
        self,
        max_retries: Optional[int] = None,
        backoff_factor: Optional[float] = None,
    ) -> None:
        """
        リトライ設定を更新します。

        Args:
            max_retries: 新しい最大リトライ回数
            backoff_factor: 新しいバックオフ係数
        """
        if max_retries is not None:
            self.max_retries = max_retries
        if backoff_factor is not None:
            self.backoff_factor = backoff_factor

    def _handle_retry_exception(
        self, e: Exception, attempt: int, operation_name: str
    ) -> Optional[Exception]:
        """
        _retry_async内の例外に対するリトライロジックを処理します。

        リトライする場合はNoneを返し、そうでない場合は発生させる例外を返します。
        """
        if attempt < self.max_retries and self._is_retryable_error(e):
            logger.warning(
                "Attempt %d/%d failed for %s: %s",
                attempt + 1,
                self.max_retries + 1,
                operation_name,
                e,
            )
            return None
        logger.error(
            "Final attempt failed for %s after %d retries: %s",
            operation_name,
            attempt,
            e,
        )
        return e
