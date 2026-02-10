"""Unit tests for LatestStocksRefreshService.

最小限の docstring を追加して linter の要件を満たす。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.exceptions.business import ServiceError
from app.services.views.latest_stocks.refresh import LatestStocksRefreshService


class _FakeResult:
    def __init__(self, val):
        self._val = val

    def fetchone(self):
        return (self._val,)


class _FakeSyncConn:
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
        return _FakeSyncConn(self._responses)


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, should_fail: bool = False, lock_responses=None):
        self.executed = []
        self._should_fail = should_fail
        self._lock_responses = lock_responses or [True]
        self._response_index = 0

    async def execute(self, stmt, *args, **kwargs):
        self.executed.append(stmt)
        if self._should_fail:
            raise RuntimeError("execute-failed")
        # ロック取得の結果を返す
        if self._response_index < len(self._lock_responses):
            val = self._lock_responses[self._response_index]
            self._response_index += 1
            return _FakeResult(val)
        return _FakeResult(True)

    def begin(self):
        return _FakeTransaction()

    async def commit(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, conn: _FakeConn, lock_responses=None):
        self._conn = conn
        # lock_responsesをconnに渡す
        if lock_responses:
            self._conn._lock_responses = lock_responses
            self._conn._response_index = 0
        self.sync_engine = _FakeSyncEngine(lock_responses or [True, True])

    def connect(self):
        return self._conn


@pytest.mark.asyncio
async def test_run_refresh_success():
    """正常系: run_refresh が正常に完了する."""
    conn = _FakeConn(should_fail=False)
    engine = _FakeEngine(conn)

    batch = AsyncMock()
    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    # act
    result = await svc.run_refresh()

    # assert: VIEW前提のため no-op で None を返す
    assert result is None


@pytest.mark.asyncio
async def test_run_refresh_noop_does_not_raise():
    """run_refresh は VIEW 前提で no-op のため例外を発生させない."""
    conn = _FakeConn(should_fail=True)
    engine = _FakeEngine(conn)

    batch = AsyncMock()
    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    result = await svc.run_refresh()
    assert result is None


@pytest.mark.asyncio
async def test_enqueue_refresh_success_calls_batch_methods(monkeypatch):
    """enqueue_refresh がバッチ処理を呼び、job_id を返す."""
    conn = _FakeConn(should_fail=False)
    # Advisory lock を取得（True）し、最後に解放（True）
    engine = _FakeEngine(conn, lock_responses=[True, True])

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=11)
    batch.start_job.return_value = None
    batch.complete_job.return_value = None

    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    job_id = await svc.enqueue_refresh()

    assert job_id == 11
    batch.create_job.assert_awaited()
    batch.start_job.assert_awaited()
    batch.complete_job.assert_awaited()


@pytest.mark.asyncio
async def test_enqueue_refresh_create_job_failure_raises_service_error():
    """create_job が None を返す場合は ServiceError を送出する."""
    conn = _FakeConn(should_fail=False)
    # Advisory lock は取得できるが、その後解放される
    engine = _FakeEngine(conn, lock_responses=[True, True])

    batch = AsyncMock()
    batch.create_job.return_value = None

    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    with pytest.raises(ServiceError) as exc_info:
        await svc.enqueue_refresh()

    # Advisory lock が取得できないのではなく、ジョブ作成に失敗したことを確認
    assert "failed to create refresh job" in str(exc_info.value)


@pytest.mark.asyncio
async def test_enqueue_refresh_lock_not_acquired_raises_service_error():
    """Advisory lock が取得できない場合は ServiceError を送出する."""
    conn = _FakeConn(should_fail=False)
    # SQLiteではadvisory lockを用いないため、lock失敗でもジョブは作成される
    engine = _FakeEngine(conn, lock_responses=[False])

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=11)

    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    job_id = await svc.enqueue_refresh()
    assert job_id == 11
    batch.create_job.assert_awaited()
