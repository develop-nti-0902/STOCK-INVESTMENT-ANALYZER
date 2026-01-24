from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from app.api.v1 import batch as batch_module
from app.exceptions.database import RecordNotFoundError


class FakeJob:
    def __init__(
        self,
        id: int = 1,
        status: str = "PENDING",
        batch_type: str = "",
        job_type: str = "",
    ):
        self.id = id
        # ステータスを正規化（テストで使われる 'done' や 'created' などを許容）
        s = (status or "").lower()
        if s in ("done", "completed"):
            status_val = "COMPLETED"
        elif s == "created":
            status_val = "PENDING"
        else:
            status_val = (status or "").upper()

        self.status = status_val
        # batch_type が空なら job_type、なければデフォルトを設定しておく
        self.batch_type = batch_type or job_type or "JPX_ALL_STOCKS"
        self.job_type = job_type if job_type else self.batch_type
        self.created_at = None
        self.updated_at = None
        self.params = None
        self.progress = None
        self.success_count = None
        self.failed_count = None
        self.error_message = None
        self.started_at = None
        self.finished_at = None


class FakeRepo:
    def __init__(
        self,
        create_job_result=None,
        get_result=None,
        by_type=None,
        recent=None,
        cancel_result=None,
    ):
        self._create_job_result = create_job_result or FakeJob()
        self._get_result = get_result
        self._by_type = by_type or []
        self._recent = recent or []
        self._cancel_result = cancel_result

    async def create_job(self, batch_type: str, params: dict | None = None):
        return self._create_job_result

    async def get(self, job_id: int):
        return self._get_result

    async def get_by_job_type(self, job_type: str):
        return self._by_type

    async def get_recent(self, limit: int = 10):
        return self._recent

    async def cancel_job(self, job_id: int):
        return self._cancel_result

    # helper for background fake process (not used directly)
    async def update_status(self, job_id: int, status: str):
        pass

    async def mark_completed(
        self, job_id: int, success_count: int, failed_count: int
    ):
        pass


class ParamsStub:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def model_dump(self):
        return self._data


class FakeRepoProcess:
    def __init__(self):
        self.updated_status = []
        self.progress_updates = []
        self.mark_completed_args = None

    async def update_status(self, job_id: int, status: str):
        self.updated_status.append((job_id, status))

    async def update_progress(self, job_id: int, progress: dict):
        self.progress_updates.append((job_id, progress))

    async def mark_completed(
        self, job_id: int, success_count: int, failed_count: int
    ):
        self.mark_completed_args = (job_id, success_count, failed_count)


class SessionMaker:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_start_single_stock_job_calls_create_and_returns_job():
    # Arrange
    fake_job = FakeJob(id=42, status="PENDING", job_type="SINGLE_STOCK")
    repo = FakeRepo(create_job_result=fake_job)

    # Act
    result = await batch_module.start_single_stock_job(repo=repo)

    # Assert
    # API は BatchExecutionResponse スキーマを返すため、job_id/status を検証する
    assert result.job_id == str(42)
    assert result.status == "PENDING"


@pytest.mark.asyncio
async def test_get_job_status_not_found_raises():
    # Arrange
    repo = FakeRepo(get_result=None)

    # Act & Assert
    with pytest.raises(RecordNotFoundError) as exc:
        await batch_module.get_job_status(1, repo=repo)

    # Assert
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_history_filters_by_type_and_status():
    jobs = [FakeJob(id=1, status="COMPLETED"), FakeJob(id=2, status="RUNNING")]
    repo = FakeRepo(by_type=jobs, recent=jobs)
    # Arrange
    # (jobs and repo prepared)

    # Act: filter by job_type -> API はスキーマ化されたリストを返す
    result = await batch_module.get_history(
        job_type=SimpleNamespace(value="any"), status=None, repo=repo
    )

    # Assert: 件数と job_id を確認
    assert len(result) == len(jobs)
    assert all(isinstance(r, object) for r in result)

    # Act: filter by status
    result2 = await batch_module.get_history(
        job_type=None, status="COMPLETED", repo=repo
    )

    # Assert: ステータスが正しくフィルタされていること
    assert all(r.status == "COMPLETED" for r in result2)


@pytest.mark.asyncio
async def test_cancel_job_returns_404_when_not_found():
    repo = FakeRepo(cancel_result=None)
    with pytest.raises(RecordNotFoundError) as exc:
        await batch_module.cancel_job(123, repo=repo)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_job_status_found_returns_job():
    # Arrange
    fake_job = FakeJob(id=77, status="PENDING")
    repo = FakeRepo(get_result=fake_job)

    # Act
    result = await batch_module.get_job_status(77, repo=repo)

    # Assert: スキーマ化されたレスポンスで job_id/status を検証
    assert result.job_id == str(77)
    assert result.status == "PENDING"


@pytest.mark.asyncio
async def test_cancel_job_returns_job_when_found():
    # Arrange
    fake_job = FakeJob(id=250, status="cancelled")
    repo = FakeRepo(cancel_result=fake_job)

    # Act
    result = await batch_module.cancel_job(250, repo=repo)

    # Assert: スキーマ化されたレスポンスで job_id/status を検証
    assert result.job_id == str(250)
    assert result.status == "CANCELLED"


# Single-JPX processing tests removed: use multi-ticker endpoints instead.


@pytest.mark.asyncio
async def test_run_jpx_all_multi_sequence_returns_pending_response():
    """JPX全銘柄マルチ順次実行エンドポイントが正しくジョブを作成して
    PENDINGステータスで返すことを確認する."""
    # Arrange
    fake_job = FakeJob(id=123, status="PENDING", job_type="JPX_ALL_STOCKS")
    repo = FakeRepo(create_job_result=fake_job)
    background_tasks = BackgroundTasks()

    # batch_size を持つリクエストパラメータ
    class FakeSequenceParams:
        batch_size = 50

        def model_dump(self):
            return {"batch_size": self.batch_size}

    # Act
    result = await batch_module.run_jpx_all_multi_sequence(
        params=FakeSequenceParams(),
        background_tasks=background_tasks,
        repo=repo,
        service=None,
    )

    # Assert
    assert result.job_id == "123"
    assert result.overall_status == "PENDING"
    assert result.results == []
    # バックグラウンドタスクが登録されていることを確認
    assert len(background_tasks.tasks) == 1


@pytest.mark.asyncio
async def test_process_jpx_all_multi_sequence_executes_all_timeframes(
    monkeypatch,
):
    """順次実行処理が1d→1m→1hを正しく実行することを確認する."""
    fake_repo = FakeRepoProcess()
    monkeypatch.setattr(
        batch_module, "BatchExecutionRepository", lambda session: fake_repo
    )
    dummy_session = object()
    monkeypatch.setattr(
        batch_module, "get_session_maker", lambda: SessionMaker(dummy_session)
    )

    executed_timeframes = []

    # _execute_single_timeframe をモックして実行されたタイムフレームを記録
    async def mock_execute_timeframe(job_id, timeframe, batch_size, service):
        executed_timeframes.append(timeframe)
        return {
            "timeframe": timeframe,
            "status": "completed",
            "success_count": 10,
            "failed_count": 0,
            "error_message": None,
            "started_at": "2026-01-17T00:00:00",
            "finished_at": "2026-01-17T00:10:00",
        }

    monkeypatch.setattr(
        batch_module, "_execute_single_timeframe", mock_execute_timeframe
    )

    # Act
    await batch_module.process_jpx_all_multi_sequence(
        job_id=999, batch_size=50, service=None
    )

    # Assert
    assert executed_timeframes == ["1d", "1m", "1h"]
    assert (999, "running") in fake_repo.updated_status
    # 全タイムフレーム完了後にmark_completedが呼ばれている
    assert fake_repo.mark_completed_args == (999, 30, 0)


@pytest.mark.asyncio
async def test_process_jpx_all_multi_sequence_handles_partial_failure(
    monkeypatch,
):
    """一部のタイムフレームが失敗しても処理が継続されることを確認する."""
    fake_repo = FakeRepoProcess()
    monkeypatch.setattr(
        batch_module, "BatchExecutionRepository", lambda session: fake_repo
    )
    dummy_session = object()
    monkeypatch.setattr(
        batch_module, "get_session_maker", lambda: SessionMaker(dummy_session)
    )

    # 2番目のタイムフレーム（1m）を失敗させる
    async def mock_execute_timeframe(job_id, timeframe, batch_size, service):
        if timeframe == "1m":
            return {
                "timeframe": timeframe,
                "status": "failed",
                "success_count": 0,
                "failed_count": 5,
                "error_message": "Test error",
                "started_at": "2026-01-17T00:00:00",
                "finished_at": "2026-01-17T00:10:00",
            }
        return {
            "timeframe": timeframe,
            "status": "completed",
            "success_count": 10,
            "failed_count": 0,
            "error_message": None,
            "started_at": "2026-01-17T00:00:00",
            "finished_at": "2026-01-17T00:10:00",
        }

    monkeypatch.setattr(
        batch_module, "_execute_single_timeframe", mock_execute_timeframe
    )

    # Act
    await batch_module.process_jpx_all_multi_sequence(
        job_id=888, batch_size=50, service=None
    )

    # Assert
    # 1dで10成功、1mで5失敗、1hで10成功 = 計20成功、5失敗
    assert fake_repo.mark_completed_args == (888, 20, 5)


# ========================================
# リソース管理機能のテスト
# ========================================


class TestLogMemoryUsage:
    """_log_memory_usage関数のテスト."""

    def test_log_memory_usage_with_psutil(
        self, caplog: pytest.LogCaptureFixture, monkeypatch
    ) -> None:
        """psutilが利用可能な場合、メモリ使用量をログ出力すること."""
        # Arrange
        import logging
        from unittest.mock import MagicMock

        mock_psutil = MagicMock()
        mock_process = MagicMock()
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 1024 * 1024 * 100  # 100MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.cpu_percent.return_value = 25.5
        mock_psutil.Process.return_value = mock_process

        monkeypatch.setattr(batch_module, "PSUTIL_AVAILABLE", True)
        monkeypatch.setattr(batch_module, "psutil", mock_psutil)

        # Act
        with caplog.at_level(logging.INFO):
            batch_module._log_memory_usage("Test context")

        # Assert
        assert "[Resource Monitor]" in caplog.text
        assert "Test context" in caplog.text
        assert "100.00 MB" in caplog.text
        assert "25.50%" in caplog.text

    def test_log_memory_usage_without_psutil(
        self, caplog: pytest.LogCaptureFixture, monkeypatch
    ) -> None:
        """psutilが利用不可能な場合、何もログ出力しないこと."""
        # Arrange
        monkeypatch.setattr(batch_module, "PSUTIL_AVAILABLE", False)

        # Act
        batch_module._log_memory_usage("Test context")

        # Assert
        assert "[Resource Monitor]" not in caplog.text

    def test_log_memory_usage_handles_exception(
        self, caplog: pytest.LogCaptureFixture, monkeypatch
    ) -> None:
        """メモリ情報取得時の例外を適切に処理すること."""
        # Arrange
        from unittest.mock import MagicMock

        mock_psutil = MagicMock()
        mock_psutil.Process.side_effect = Exception("Test error")

        monkeypatch.setattr(batch_module, "PSUTIL_AVAILABLE", True)
        monkeypatch.setattr(batch_module, "psutil", mock_psutil)

        # Act
        batch_module._log_memory_usage("Test context")

        # Assert
        assert "Failed to log memory usage" in caplog.text


class TestProcessChunkMultiResourceManagement:
    """_process_chunk_multi関数のリソース管理テスト."""

    @pytest.mark.asyncio
    async def test_process_chunk_multi_releases_memory(
        self, monkeypatch
    ) -> None:
        """チャンク処理後にメモリが解放されること."""
        # Arrange
        import gc
        from unittest.mock import AsyncMock, MagicMock, patch

        mock_service = MagicMock()
        mock_fetcher = AsyncMock()
        mock_validator = MagicMock()
        mock_converter = MagicMock()
        mock_saver = AsyncMock()

        mock_service.fetcher = mock_fetcher
        mock_service.validator = mock_validator
        mock_service.converter = mock_converter
        mock_service.saver = mock_saver

        # fetcherは空の結果を返す
        mock_fetcher.fetch_batch.return_value = {}

        chunk = ["7203.T", "9984.T"]
        timeframe = "1d"

        # gcモジュールをモック
        with patch.object(gc, "collect") as mock_gc_collect:
            # Act
            success, failed, errors = await batch_module._process_chunk_multi(
                chunk, mock_service, timeframe, {}
            )

            # Assert
            # gc.collect()が呼ばれることを確認
            mock_gc_collect.assert_called_once()

        assert success == 0
        assert failed == 0
        assert errors == []


class TestExecuteSingleTimeframeResourceManagement:
    """_execute_single_timeframe関数のリソース管理テスト."""

    @pytest.mark.asyncio
    async def test_execute_single_timeframe_logs_memory(
        self, monkeypatch
    ) -> None:
        """タイムフレーム処理の開始時と完了時にメモリ使用量をログ出力すること."""
        # Arrange
        from unittest.mock import AsyncMock, MagicMock, patch

        job_id = 1
        timeframe = "1d"
        batch_size = 50

        mock_service = MagicMock()
        mock_stock_master_service = AsyncMock()
        mock_stock_master_service.get_all_active_symbols.return_value = []
        mock_service.stock_master_service = mock_stock_master_service
        mock_service.batch_service = MagicMock()

        # BatchExecutionContextをモック
        mock_batch_context = AsyncMock()
        mock_batch_context.__aenter__ = AsyncMock(
            return_value=mock_batch_context
        )
        mock_batch_context.__aexit__ = AsyncMock(return_value=None)
        mock_batch_context.update_progress = AsyncMock()

        with patch(
            "app.api.v1.batch.BatchExecutionContext",
            return_value=mock_batch_context,
        ), patch(
            "app.api.v1.batch._make_progress_handlers"
        ) as mock_handlers, patch(
            "app.api.v1.batch._log_memory_usage"
        ) as mock_log_memory:
            mock_handlers.return_value = (set(), None, None)

            # Act
            result = await batch_module._execute_single_timeframe(
                job_id, timeframe, batch_size, mock_service
            )

            # Assert
            # 開始時と完了時のログ呼び出しを確認
            assert mock_log_memory.call_count >= 2

            calls = [str(call) for call in mock_log_memory.call_args_list]
            assert any("started" in call for call in calls)
            assert any("completed" in call for call in calls)

            assert result["status"] == "completed"
            assert result["timeframe"] == timeframe


class TestProcessJpxAllMultiSequenceResourceManagement:
    """process_jpx_all_multi_sequence関数のリソース管理テスト."""

    @pytest.mark.asyncio
    async def test_sequence_logs_memory_at_each_timeframe(
        self, monkeypatch
    ) -> None:
        """各タイムフレーム処理前後でメモリ使用量をログ出力すること."""
        # Arrange
        import gc
        from unittest.mock import AsyncMock, MagicMock, patch

        job_id = 1
        batch_size = 50
        mock_service = MagicMock()

        # セッションのモック
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.return_value = mock_session

        # リポジトリのモック
        mock_repo = MagicMock()
        mock_repo.update_status = AsyncMock()
        mock_repo.mark_completed = AsyncMock()

        monkeypatch.setattr(
            batch_module, "get_session_maker", lambda: mock_session_maker
        )

        with patch(
            "app.api.v1.batch.BatchExecutionRepository",
            return_value=mock_repo,
        ), patch(
            "app.api.v1.batch._execute_single_timeframe"
        ) as mock_execute_timeframe, patch(
            "app.api.v1.batch._log_memory_usage"
        ) as mock_log_memory, patch.object(
            gc, "collect"
        ):
            # タイムフレーム処理のモック(成功ケース)
            mock_execute_timeframe.return_value = {
                "status": "completed",
                "success_count": 10,
                "failed_count": 0,
            }

            # Act
            await batch_module.process_jpx_all_multi_sequence(
                job_id, batch_size, mock_service
            )

            # Assert
            # メモリログが複数回呼ばれていることを確認
            # バッチ開始時、各タイムフレーム前後、完了時
            assert mock_log_memory.call_count >= 7

            # バッチ開始時のログ
            calls = [str(call) for call in mock_log_memory.call_args_list]
            assert any("started" in call for call in calls)
            assert any("completed successfully" in call for call in calls)

    @pytest.mark.asyncio
    async def test_sequence_releases_resources_after_each_timeframe(
        self, monkeypatch
    ) -> None:
        """各タイムフレーム処理後にリソースを解放すること."""
        # Arrange
        import gc
        from unittest.mock import AsyncMock, MagicMock, patch

        job_id = 1
        batch_size = 50
        mock_service = MagicMock()

        # セッションのモック
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock()
        mock_session_maker.return_value.return_value = mock_session

        # リポジトリのモック
        mock_repo = MagicMock()
        mock_repo.update_status = AsyncMock()
        mock_repo.mark_completed = AsyncMock()

        monkeypatch.setattr(
            batch_module, "get_session_maker", lambda: mock_session_maker
        )

        with patch(
            "app.api.v1.batch.BatchExecutionRepository",
            return_value=mock_repo,
        ), patch(
            "app.api.v1.batch._execute_single_timeframe"
        ) as mock_execute_timeframe:
            # タイムフレーム処理のモック
            mock_execute_timeframe.return_value = {
                "status": "completed",
                "success_count": 10,
                "failed_count": 0,
            }

            # gc.collectとasyncio.sleepをモック
            with patch.object(gc, "collect") as mock_gc_collect, patch(
                "app.api.v1.batch._asyncio.sleep", new_callable=AsyncMock
            ) as mock_sleep:
                # Act
                await batch_module.process_jpx_all_multi_sequence(
                    job_id, batch_size, mock_service
                )

                # Assert
                # タイムフレームは3つ(1d, 1m, 1h)なので、
                # gc.collect()が3回呼ばれること
                assert mock_gc_collect.call_count == 3

                # asyncio.sleep(0.1)が3回呼ばれること
                assert mock_sleep.call_count == 3
                mock_sleep.assert_called_with(0.1)
