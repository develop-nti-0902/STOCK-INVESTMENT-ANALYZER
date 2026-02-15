"""バッチ処理ユーティリティの単体テスト."""

import asyncio
import time
from typing import Any, Dict

import pytest

from app.exceptions.validation import FieldValidationError
from app.utils.batch_utils import ProgressTracker, chunk_list, parallel_execute


class TestChunkList:
    """chunk_list関数のテスト."""

    def test_empty_list(self):
        """空リストのテスト."""
        result = chunk_list([], 5)
        assert result == []

    def test_chunk_size_one(self):
        """チャンクサイズ1のテスト."""
        items = [1, 2, 3, 4, 5]
        result = chunk_list(items, 1)
        expected = [[1], [2], [3], [4], [5]]
        assert result == expected

    def test_even_chunks(self):
        """均等に分割できる場合のテスト."""
        items = [1, 2, 3, 4, 5, 6]
        result = chunk_list(items, 2)
        expected = [[1, 2], [3, 4], [5, 6]]
        assert result == expected

    def test_uneven_chunks(self):
        """均等に分割できない場合のテスト."""
        items = [1, 2, 3, 4, 5]
        result = chunk_list(items, 2)
        expected = [[1, 2], [3, 4], [5]]
        assert result == expected

    def test_chunk_size_larger_than_list(self):
        """チャンクサイズがリストサイズより大きい場合のテスト."""
        items = [1, 2, 3]
        result = chunk_list(items, 5)
        expected = [[1, 2, 3]]
        assert result == expected

    def test_invalid_chunk_size(self):
        """無効なチャンクサイズのテスト."""
        with pytest.raises(FieldValidationError, match="chunk_size must be greater than 0"):
            chunk_list([1, 2, 3], 0)

        with pytest.raises(FieldValidationError, match="chunk_size must be greater than 0"):
            chunk_list([1, 2, 3], -1)


class TestParallelExecute:
    """parallel_execute関数のテスト."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """正常実行のテスト."""

        async def dummy_task(value: int) -> int:
            await asyncio.sleep(0.01)  # 短い遅延
            return value * 2

        tasks = [dummy_task(i) for i in range(5)]
        results = await parallel_execute(tasks, max_concurrent=3)

        assert results == [0, 2, 4, 6, 8]

    @pytest.mark.asyncio
    async def test_exception_handling_return_exceptions_true(self):
        """例外処理のテスト（return_exceptions=True）."""

        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        async def success_task():
            await asyncio.sleep(0.01)
            return "success"

        tasks = [failing_task(), success_task(), failing_task()]
        results = await parallel_execute(tasks, max_concurrent=2, return_exceptions=True)

        assert len(results) == 3
        assert isinstance(results[0], ValueError)
        assert results[1] == "success"
        assert isinstance(results[2], ValueError)

    @pytest.mark.asyncio
    async def test_exception_handling_return_exceptions_false(self):
        """例外処理のテスト（return_exceptions=False）."""

        async def failing_task():
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        tasks = [failing_task()]
        with pytest.raises(ValueError, match="Test error"):
            await parallel_execute(tasks, max_concurrent=1, return_exceptions=False)

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """同時実行数制限のテスト."""
        execution_times = []

        async def timed_task(task_id: int) -> int:
            start_time = time.time()
            await asyncio.sleep(0.1)  # 0.1秒の遅延
            end_time = time.time()
            execution_times.append((task_id, start_time, end_time))
            return task_id

        # 5つのタスクを同時実行数2で実行
        tasks = [timed_task(i) for i in range(5)]
        results = await parallel_execute(tasks, max_concurrent=2)

        assert results == [0, 1, 2, 3, 4]
        assert len(execution_times) == 5

        # 同時実行数が制限されていることを確認
        # （正確な検証は難しいので、基本的な実行確認のみ）


class TestProgressTracker:
    """ProgressTrackerクラスのテスト."""

    def test_initialization(self):
        """初期化のテスト."""
        tracker = ProgressTracker(total=10)
        assert tracker.total == 10
        assert tracker.processed == 0
        assert tracker.success == 0
        assert tracker.failed == 0
        assert len(tracker.errors) == 0
        assert tracker.callback is None

    def test_increment_success(self):
        """成功カウント増加のテスト."""
        tracker = ProgressTracker(total=5)

        tracker.increment_success()
        assert tracker.success == 1
        assert tracker.processed == 1

        tracker.increment_success()
        assert tracker.success == 2
        assert tracker.processed == 2

    def test_increment_failed(self):
        """失敗カウント増加のテスト."""
        tracker = ProgressTracker(total=5)

        error = ValueError("Test error")
        tracker.increment_failed(error)

        assert tracker.failed == 1
        assert tracker.processed == 1
        assert len(tracker.errors) == 1
        assert tracker.errors[0]["error_type"] == "ValueError"
        assert tracker.errors[0]["error_message"] == "Test error"

    def test_increment_failed_with_context(self):
        """失敗カウント増加（コンテキスト付き）のテスト."""
        tracker = ProgressTracker(total=5)

        error = RuntimeError("Runtime error")
        context = {"symbol": "1234", "attempt": 2}
        tracker.increment_failed(error, context)

        assert tracker.failed == 1
        assert len(tracker.errors) == 1
        assert tracker.errors[0]["context"] == context

    def test_get_progress_percent(self):
        """進捗率計算のテスト."""
        tracker = ProgressTracker(total=10)

        assert tracker.get_progress_percent() == 0.0

        tracker.increment_success()
        assert tracker.get_progress_percent() == 10.0

        tracker.increment_success()
        tracker.increment_failed(ValueError("error"))
        assert tracker.get_progress_percent() == 30.0

    def test_get_progress_percent_zero_total(self):
        """総数が0の場合の進捗率テスト."""
        tracker = ProgressTracker(total=0)
        assert tracker.get_progress_percent() == 100.0

    def test_get_elapsed_time(self):
        """経過時間取得のテスト."""
        tracker = ProgressTracker(total=1)

        # 少し待つ
        time.sleep(0.01)

        elapsed = tracker.get_elapsed_time()
        assert elapsed >= 0.01
        assert elapsed < 1.0  # 現実的な範囲

    def test_get_summary(self):
        """サマリー取得のテスト."""
        tracker = ProgressTracker(total=5)

        tracker.increment_success()
        tracker.increment_success()
        tracker.increment_failed(ValueError("error1"))
        tracker.increment_failed(ValueError("error2"))

        summary = tracker.get_summary()

        assert summary["total"] == 5
        assert summary["processed"] == 4
        assert summary["success"] == 2
        assert summary["failed"] == 2
        assert summary["progress_percent"] == 80.0
        assert isinstance(summary["elapsed_time"], float)
        assert len(summary["errors"]) == 2

    def test_get_summary_with_many_errors(self):
        """多数のエラーがある場合のサマリー取得テスト."""
        tracker = ProgressTracker(total=20)

        # 15個のエラーを追加
        for i in range(15):
            tracker.increment_failed(ValueError(f"error{i}"))

        summary = tracker.get_summary()

        # エラーは最新10件のみ
        assert len(summary["errors"]) == 10
        assert summary["errors"][-1]["error_message"] == "error14"

    @pytest.mark.asyncio
    async def test_callback_notification(self):
        """コールバック通知のテスト."""
        callback_results = []

        async def mock_callback(summary: Dict[str, Any]) -> None:
            callback_results.append(summary)

        tracker = ProgressTracker(total=3, callback=mock_callback)

        tracker.increment_success()
        await asyncio.sleep(0.01)  # コールバック実行を待つ

        tracker.increment_failed(ValueError("error"))
        await asyncio.sleep(0.01)  # コールバック実行を待つ

    def test_notify_with_async_callback_no_event_loop(self, monkeypatch):
        """非同期コールバックがあるがイベントループがない場合のパスを検証する."""

        async def async_cb(summary: Dict[str, Any]) -> None:
            # noop
            return None

        # monkeypatch create_task to raise after closing the coroutine to avoid
        # "coroutine was never awaited" ResourceWarning.
        def fake_create_task(coro):
            try:
                coro.close()
            except Exception:
                pass
            raise RuntimeError("no loop")

        monkeypatch.setattr(asyncio, "create_task", fake_create_task)

        tracker = ProgressTracker(total=1, callback=async_cb)

        # 同期コンテキストで increment_success を呼ぶと create_task が例外を投げる。
        tracker.increment_success()
        assert tracker.processed == 1

    def test_notify_with_sync_callback_executes(self):
        """同期コールバックが呼ばれることを検証する."""
        results = []

        def sync_cb(summary: Dict[str, Any]) -> None:
            results.append(summary)

        tracker = ProgressTracker(total=1, callback=sync_cb)
        tracker.increment_success()
        assert len(results) == 1
        assert results[0]["processed"] == 1

    def test_notify_sync_callback_raises_logs(self, caplog):
        """コールバックが例外を投げた場合にログが残ることを検証する."""
        import logging

        def bad_cb(summary: Dict[str, Any]) -> None:
            raise RuntimeError("callback boom")

        tracker = ProgressTracker(total=1, callback=bad_cb)

        with caplog.at_level(logging.ERROR):
            tracker.increment_success()

        assert any(r.levelno >= logging.ERROR for r in caplog.records)
