import asyncio
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1 import batch as batch_module


class FakeJob:
    def __init__(
        self,
        id: int = 1,
        status: str = "PENDING",
        batch_type: str = "",
        job_type: str = "",
    ):
        self.id = id
        self.status = status
        self.batch_type = batch_type
        # job_type がない場合は batch_type を使う
        self.job_type = job_type if job_type else batch_type
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

    async def create_job(self, batch_type: str):
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
    assert result.id == 42
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
    assert result.id == 99
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
    with pytest.raises(HTTPException) as exc:
        await batch_module.get_job_status(1, repo=repo)

    # Assert
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_history_filters_by_type_and_status():
    jobs = [FakeJob(id=1, status="done"), FakeJob(id=2, status="running")]
    repo = FakeRepo(by_type=jobs, recent=jobs)
    # Arrange
    # (jobs and repo prepared)

    # Act: filter by job_type
    result = await batch_module.get_history(
        job_type=SimpleNamespace(value="any"), status=None, repo=repo
    )

    # Assert
    assert result == jobs

    # Act: filter by status
    result2 = await batch_module.get_history(
        job_type=None, status="done", repo=repo
    )

    # Assert
    assert all(r.status == "done" for r in result2)


@pytest.mark.asyncio
async def test_cancel_job_returns_404_when_not_found():
    repo = FakeRepo(cancel_result=None)
    with pytest.raises(HTTPException) as exc:
        await batch_module.cancel_job(123, repo=repo)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_job_status_found_returns_job():
    # Arrange
    fake_job = FakeJob(id=77, status="created")
    repo = FakeRepo(get_result=fake_job)

    # Act
    result = await batch_module.get_job_status(77, repo=repo)

    # Assert
    assert result is fake_job


@pytest.mark.asyncio
async def test_cancel_job_returns_job_when_found():
    # Arrange
    fake_job = FakeJob(id=250, status="cancelled")
    repo = FakeRepo(cancel_result=fake_job)

    # Act
    result = await batch_module.cancel_job(250, repo=repo)

    # Assert
    assert result is fake_job


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
            self, timeframe, start_date, end_date, market, progress_callback
        ):
            # 進捗コールバックを数回呼ぶ
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
