from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.batch import refresh_latest_stocks as mod


class _FakeResult:
    def __init__(self, val):
        self._val = val

    def fetchone(self):
        return (self._val,)


class _FakeConn:
    def __init__(self, responses):
        # responses is an iterable of return values for execute().fetchone()
        self._responses = list(responses)

    def execute(self, *args, **kwargs):
        val = self._responses[0] if self._responses else False
        return _FakeResult(val)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeSyncEngine:
    def __init__(self, responses):
        self._responses = list(responses)

    def connect(self):
        # return a fresh conn that will report the configured responses
        return _FakeConn(self._responses)


class _FakeEngine:
    def __init__(self, responses):
        self.sync_engine = _FakeSyncEngine(responses)


@pytest.mark.asyncio
async def test_refresh_runs_when_lock_acquired(monkeypatch):
    # arrange
    fake_engine = _FakeEngine([True])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine)

    # fake batch service (BatchExecutionService-like)
    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=1)
    batch.start_job.return_value = None
    batch.get_job_status.return_value = SimpleNamespace(
        processed_stocks=0, successful_stocks=0, failed_stocks=0
    )
    batch.complete_job.return_value = None

    called = {}

    class FakeSvc:
        def __init__(self, batch_service, engine=None):
            called["init_args"] = (batch_service, engine)

        async def run_refresh(self):
            called["run"] = True

    monkeypatch.setattr(mod, "LatestStocksRefreshService", FakeSvc)

    # act
    await mod.refresh_latest_stocks_job(
        batch_service=batch, engine=fake_engine
    )

    # assert
    assert called.get("run") is True
    batch.create_job.assert_awaited()


@pytest.mark.asyncio
async def test_no_run_when_lock_not_acquired(monkeypatch):
    fake_engine = _FakeEngine([False])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine)

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=2)
    batch.start_job.return_value = None

    class FakeSvc:
        def __init__(self, *a, **k):
            pass

        async def run_refresh(self):
            raise RuntimeError("should not be called")

    monkeypatch.setattr(mod, "LatestStocksRefreshService", FakeSvc)

    await mod.refresh_latest_stocks_job(
        batch_service=batch, engine=fake_engine
    )

    # run_refresh should not have been called; create_job still awaited
    batch.create_job.assert_awaited()


@pytest.mark.asyncio
async def test_release_failure_logs_but_run_called(monkeypatch):
    # acquire True, release False
    fake_engine = _FakeEngine([True])
    # monkeypatch connect to return conn that will return True for acquire
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine)

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=3)
    batch.start_job.return_value = None
    batch.get_job_status.return_value = SimpleNamespace(
        processed_stocks=0, successful_stocks=0, failed_stocks=0
    )

    class FakeSvc:
        def __init__(self, *a, **k):
            pass

        async def run_refresh(self):
            return None

    monkeypatch.setattr(mod, "LatestStocksRefreshService", FakeSvc)

    # Patch _release to return False to simulate unlock failure
    def fake_release():
        return False

    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine)

    # run
    await mod.refresh_latest_stocks_job(
        batch_service=batch, engine=fake_engine
    )

    batch.create_job.assert_awaited()


@pytest.mark.asyncio
async def test_exception_in_run_refresh_propagates_and_marks_failed(
    monkeypatch,
):
    fake_engine = _FakeEngine([True])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine)

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=4)
    batch.start_job.return_value = None
    batch.fail_job.return_value = None

    class FakeSvc:
        def __init__(self, *a, **k):
            pass

        async def run_refresh(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(mod, "LatestStocksRefreshService", FakeSvc)

    with pytest.raises(RuntimeError):
        await mod.refresh_latest_stocks_job(
            batch_service=batch, engine=fake_engine
        )

    # ensure fail_job was called by context manager
    batch.create_job.assert_awaited()
    batch.fail_job.assert_awaited()
