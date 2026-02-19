"""リトライデコレータ.

一時的なエラーに対して自動リトライを行うデコレータを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

import asyncio
import functools
import inspect
import time
from typing import Any, Callable, ParamSpec, TypeVar

# 戻り値の型パラメータ
P = ParamSpec("P")
R = TypeVar("R")


# 汎用的な `ParamSpec` と `Any` を使用して、デコレータが同期関数
# または非同期関数のいずれにも対応するように型注釈を緩和しています。
# これにより型チェッカが `await` に対して誤ったエラーを報告するのを防ぎます。


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """エラー発生時に自動でリトライを行うデコレータを返す.

    Args:
        max_retries (int): 最大リトライ回数（デフォルト: 3）
        delay (float): 初回待機時間（秒）（デフォルト: 1.0）
        backoff (float): 各試行での倍率（デフォルト: 2.0）
        exceptions (tuple[type[Exception], ...]): リトライ対象例外のタプル

    Returns:
        Callable: デコレータ関数

    Notes:
        - 非同期/同期関数両対応
        - 指数バックオフ戦略を使用
    """

    def decorator(func: Callable[P, Any]) -> Callable[P, Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # 待機時間を計算（指数バックオフ）
                        wait_time = delay * (backoff**attempt)

                        # ロガー統合時にリトライログを追加予定

                        await asyncio.sleep(wait_time)
                    else:
                        # 最大リトライ回数に達した
                        # ロガー統合時に最終失敗ログを追加予定
                        break

            # 全てのリトライが失敗した場合
            if last_exception:
                raise last_exception
            # 理論的にはここには到達しない
            raise RuntimeError("Retry logic error: no exception recorded")

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # 待機時間を計算（指数バックオフ）
                        wait_time = delay * (backoff**attempt)

                        # ロガー統合時にリトライログを追加予定

                        time.sleep(wait_time)
                    else:
                        # 最大リトライ回数に達した
                        # ロガー統合時に最終失敗ログを追加予定
                        break

            # 全てのリトライが失敗した場合
            if last_exception:
                raise last_exception
            # 理論的にはここには到達しない
            raise RuntimeError("Retry logic error: no exception recorded")

        # 関数が非同期かどうかで切り替え
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper

    return decorator


def retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, Any]], Callable[P, Any]]:
    """互換性ラッパー: 旧APIの `retries` 引数を受け取る。

    内部で `retry_on_error` を呼び出します。
    """
    return retry_on_error(max_retries=retries, delay=delay, backoff=backoff, exceptions=exceptions)


__all__ = ["retry_on_error", "retry"]
