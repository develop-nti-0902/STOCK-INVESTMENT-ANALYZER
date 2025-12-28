from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1 import batch as batch_module


class FakeJob:
    def __init__(
        self, id: int = 1, status: str = "pending", batch_type: str = ""
    ):
        self.id = id
        self.status = status
        self.batch_type = batch_type


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


@pytest.mark.asyncio
async def test_start_single_stock_job_calls_create_and_returns_job():
    fake_job = FakeJob(id=42, status="created")
    repo = FakeRepo(create_job_result=fake_job)

    result = await batch_module.start_single_stock_job(
        params=ParamsStub(), repo=repo
    )

    assert result is fake_job
    assert result.id == 42


@pytest.mark.asyncio
async def test_start_jpx_all_job_schedules_background_task(monkeypatch):
    fake_job = FakeJob(id=99, status="created")
    repo = FakeRepo(create_job_result=fake_job)
    background_tasks = BackgroundTasks()
    result = await batch_module.start_jpx_all_job(
        params=ParamsStub(), background_tasks=background_tasks, repo=repo
    )

    assert result is fake_job
    # BackgroundTasks にタスクが登録されていることを確認
    assert len(background_tasks.tasks) == 1
    # BackgroundTask オブジェクトの中に登録されたコール可能オブジェクトを検査
    found = False
    for t in background_tasks.tasks:
        if getattr(t, "func", None) is batch_module.process_jpx_all_stocks:
            found = True
            break

    assert found is True


@pytest.mark.asyncio
async def test_get_job_status_not_found_raises():
    repo = FakeRepo(get_result=None)
    with pytest.raises(HTTPException) as exc:
        await batch_module.get_job_status(1, repo=repo)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_history_filters_by_type_and_status():
    jobs = [FakeJob(id=1, status="done"), FakeJob(id=2, status="running")]
    repo = FakeRepo(by_type=jobs, recent=jobs)

    # filter by job_type
    result = await batch_module.get_history(
        job_type=SimpleNamespace(value="any"), status=None, repo=repo
    )
    assert result == jobs

    # filter by status
    result2 = await batch_module.get_history(
        job_type=None, status="done", repo=repo
    )
    assert all(r.status == "done" for r in result2)


@pytest.mark.asyncio
async def test_cancel_job_returns_404_when_not_found():
    repo = FakeRepo(cancel_result=None)
    with pytest.raises(HTTPException) as exc:
        await batch_module.cancel_job(123, repo=repo)

    assert exc.value.status_code == 404
