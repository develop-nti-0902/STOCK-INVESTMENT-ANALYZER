"""バッチ処理ユーティリティモジュール

JPX全銘柄一括取得機能のためのバッチ処理ユーティリティを提供します。
リスト分割、並列実行制御、進捗トラッキング機能を含みます。
"""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
)

T = TypeVar("T")


def chunk_list(items: List[T], chunk_size: int) -> List[List[T]]:
    """
    リストを指定サイズのチャンクに分割

    Args:
        items: 分割対象リスト
        chunk_size: チャンクサイズ

    Returns:
        分割されたリストのリスト

    Raises:
        ValueError: chunk_sizeが1未満の場合
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be greater than 0")

    return [
        items[i : i + chunk_size] for i in range(0, len(items), chunk_size)
    ]


async def parallel_execute(
    tasks: List[Awaitable[T]],
    max_concurrent: int = 20,
    return_exceptions: bool = True,
) -> List[Union[T, Exception, BaseException]]:
    """
    タスクを並列実行（同時実行数制限付き）

    Args:
        tasks: 実行するコルーチンのリスト
        max_concurrent: 最大同時実行数
        return_exceptions: 例外を結果に含めるか

    Returns:
        実行結果のリスト（例外を含む場合あり）
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_with_semaphore(
        task: Awaitable[T],
    ) -> Union[T, Exception]:
        async with semaphore:
            try:
                return await task
            except Exception as e:
                if return_exceptions:
                    return e
                raise

    return await asyncio.gather(
        *(execute_with_semaphore(task) for task in tasks),
        return_exceptions=return_exceptions,
    )


class ProgressTracker:
    """
    バッチ処理の進捗を追跡するクラス

    Attributes:
        total: 総アイテム数
        processed: 処理済み数
        success: 成功数
        failed: 失敗数
        errors: エラーリスト
        start_time: 開始時刻
    """

    def __init__(
        self,
        total: int,
        callback: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    ):
        """
        Args:
            total: 総アイテム数
            callback: 進捗コールバック関数
        """
        self.total = total
        self.processed = 0
        self.success = 0
        self.failed = 0
        self.errors: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.callback = callback

    def increment_success(self) -> None:
        """成功カウントを増加"""
        self.success += 1
        self.processed += 1
        self._notify()

    def increment_failed(
        self, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """失敗カウントを増加し、エラーを記録"""
        self.failed += 1
        self.processed += 1

        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": time.time(),
        }
        if context:
            error_info["context"] = context

        self.errors.append(error_info)
        self._notify()

    def get_progress_percent(self) -> float:
        """進捗率（パーセント）を取得"""
        if self.total == 0:
            return 100.0
        return (self.processed / self.total) * 100.0

    def get_elapsed_time(self) -> float:
        """経過時間（秒）を取得"""
        return time.time() - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """進捗サマリーを取得"""
        return {
            "total": self.total,
            "processed": self.processed,
            "success": self.success,
            "failed": self.failed,
            "progress_percent": self.get_progress_percent(),
            "elapsed_time": self.get_elapsed_time(),
            "errors": self.errors[-10:],  # 最新10件のエラーのみ
        }

    def _notify(self) -> None:
        """コールバック関数経由で進捗を通知"""
        if self.callback:
            try:
                # 同期的にコールバックを実行（実際の使用ではイベントループ内で呼び出される）

                if inspect.iscoroutinefunction(self.callback):
                    # 非同期コールバックの場合はタスクを作成
                    try:
                        asyncio.create_task(self.callback(self.get_summary()))
                    except RuntimeError:
                        # イベントループがない場合は同期的に呼び出せないのでスキップ
                        pass
                else:
                    # 同期コールバックの場合は直接呼び出し
                    self.callback(self.get_summary())
            except Exception:
                pass
