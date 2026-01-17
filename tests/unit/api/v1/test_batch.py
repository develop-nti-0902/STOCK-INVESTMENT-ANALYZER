import asyncio
from datetime import date
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
async def test_start_jpx_all_job_schedules_background_task(monkeypatch):
    fake_job = FakeJob(id=99, status="PENDING", job_type="JPX_ALL_STOCKS")
    repo = FakeRepo(create_job_result=fake_job)
    background_tasks = BackgroundTasks()
    # Arrange
    # (repo, background_tasks already prepared)

    # Act
    result = await batch_module.start_jpx_all_job(
        params=ParamsStub(), background_tasks=background_tasks, repo=repo
    )

    # Assert
    # API は BatchExecutionResponse スキーマを返すため、job_id/status を検証する
    assert result.job_id == str(99)
    assert result.status == "PENDING"
    # BackgroundTasks にタスクが登録されていることを確認する
    assert len(background_tasks.tasks) == 1
    # BackgroundTask オブジェクトの中に登録されたコール可能オブジェクトを検査する
    found = False
    for t in background_tasks.tasks:
        if getattr(t, "func", None) is batch_module.process_jpx_all_stocks:
            found = True
            break

    assert found is True


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


@pytest.mark.asyncio
async def test_process_jpx_all_stocks_success(monkeypatch):
    fake_repo = FakeRepoProcess()

    # リポジトリのファクトリをパッチしてテスト用のリポジトリを返す
    monkeypatch.setattr(
        batch_module, "BatchExecutionRepository", lambda session: fake_repo
    )

    # セッションメーカーをパッチしてダミーセッションを返す
    dummy_session = object()
    monkeypatch.setattr(
        batch_module, "get_session_maker", lambda: SessionMaker(dummy_session)
    )

    # 提供された進捗コールバックを呼び、結果カウントを返すフェイクサービス
    class FakeService:
        async def fetch_all_jpx_stocks(
            self, timeframe, market=None, progress_callback=None
        ):
            # 進捗コールバックを数回呼ぶ
            if progress_callback:
                progress_callback({"progress": 10})
                progress_callback({"progress": 50})
            return {"success": "3", "failed": "1"}

    service = FakeService()

    # プロセスを実行する
    await batch_module.process_jpx_all_stocks(
        7, {"timeframe": "1d", "start_date": date.today()}, service
    )

    # create_task で作成されたバックグラウンドタスクを実行させるため待機
    await asyncio.sleep(0.05)

    # ジョブが running に更新され、正しいカウントで完了マークされたことを検証
    assert (7, "running") in fake_repo.updated_status
    assert fake_repo.mark_completed_args == (7, 3, 1)
    # 進捗更新が記録されていることを確認
    assert any(p for (_, p) in fake_repo.progress_updates)


@pytest.mark.asyncio
async def test_process_jpx_all_stocks_failure_marks_failed(monkeypatch):
    fake_repo = FakeRepoProcess()
    monkeypatch.setattr(
        batch_module, "BatchExecutionRepository", lambda session: fake_repo
    )
    dummy_session = object()
    monkeypatch.setattr(
        batch_module, "get_session_maker", lambda: SessionMaker(dummy_session)
    )

    class FailingService:
        async def fetch_all_jpx_stocks(self, *args, **kwargs):
            raise RuntimeError("boom")

    service = FailingService()

    await batch_module.process_jpx_all_stocks(13, {}, service)

    # どの非同期タスクも実行されるように待機
    await asyncio.sleep(0.05)

    # 失敗時にはリポジトリのステータスが failed に更新されているはず
    assert (13, "failed") in fake_repo.updated_status


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
