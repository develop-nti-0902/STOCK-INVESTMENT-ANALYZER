from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.exceptions.business import ServiceError
from app.services.views.latest_stocks.refresh import LatestStocksRefreshService


class _FakeConn:
    def __init__(self, should_fail: bool = False):
        self.executed = []
        self._should_fail = should_fail

    async def execute(self, stmt, *args, **kwargs):
        self.executed.append(stmt)
        if self._should_fail:
            raise RuntimeError("execute-failed")
        return None

    async def commit(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def connect(self):
        return self._conn


@pytest.mark.asyncio
async def test_run_refresh_success():
    """正常系: run_refresh が正常に完了する。"""
    conn = _FakeConn(should_fail=False)
    engine = _FakeEngine(conn)

    batch = AsyncMock()
    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    # act
    await svc.run_refresh()

    # assert: SQLが実行された
    assert any("REFRESH MATERIALIZED VIEW" in str(s) for s in conn.executed)


@pytest.mark.asyncio
async def test_run_refresh_failure_raises_service_error():
    """異常系: DB実行時の例外は ServiceError になる。"""
    conn = _FakeConn(should_fail=True)
    engine = _FakeEngine(conn)

    batch = AsyncMock()
    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    with pytest.raises(ServiceError):
        await svc.run_refresh()


@pytest.mark.asyncio
async def test_enqueue_refresh_success_calls_batch_methods(monkeypatch):
    """enqueue_refresh がバッチ処理を呼び、job_id を返す。"""
    conn = _FakeConn(should_fail=False)
    engine = _FakeEngine(conn)

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
    """create_job が None を返す場合は ServiceError を送出する。"""
    conn = _FakeConn(should_fail=False)
    engine = _FakeEngine(conn)

    batch = AsyncMock()
    batch.create_job.return_value = None

    svc = LatestStocksRefreshService(batch_service=batch, engine=engine)

    with pytest.raises(ServiceError):
        await svc.enqueue_refresh()
