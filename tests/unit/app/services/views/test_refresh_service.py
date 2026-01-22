from types import SimpleNamespace

import pytest

from app.exceptions.business import ServiceError
from app.services.views.refresh_service import LatestStocksRefreshService


@pytest.mark.asyncio
async def test_enqueue_refresh_returns_job_id() -> None:
    class FakeBatch:
        async def create_job(self, job_type: str):
            return SimpleNamespace(id=123)

    svc = LatestStocksRefreshService(batch_service=FakeBatch())
    jid = await svc.enqueue_refresh()
    assert jid == 123


@pytest.mark.asyncio
async def test_run_refresh_executes_refresh_sql() -> None:
    executed = []

    class DummyConn:
        def execute(self, stmt):
            executed.append(str(stmt))

    class DummyCtx:
        def __init__(self, conn):
            self.conn = conn

        def __enter__(self):
            return self.conn

        def __exit__(self, exc_type, exc, tb):
            return False

    class SyncEngine:
        def __init__(self, conn):
            self._conn = conn

        def connect(self):
            return DummyCtx(self._conn)

    engine = SimpleNamespace(sync_engine=SyncEngine(DummyConn()))
    svc = LatestStocksRefreshService(
        batch_service=SimpleNamespace(), engine=engine
    )

    await svc.run_refresh()

    assert any("REFRESH MATERIALIZED VIEW" in s for s in executed)


@pytest.mark.asyncio
async def test_run_refresh_raises_service_error_on_execute_failure() -> None:
    class FailingConn:
        def execute(self, stmt):
            raise RuntimeError("boom")

    class DummyCtx:
        def __init__(self, conn):
            self.conn = conn

        def __enter__(self):
            return self.conn

        def __exit__(self, exc_type, exc, tb):
            return False

    class SyncEngine:
        def __init__(self, conn):
            self._conn = conn

        def connect(self):
            return DummyCtx(self._conn)

    engine = SimpleNamespace(sync_engine=SyncEngine(FailingConn()))
    svc = LatestStocksRefreshService(
        batch_service=SimpleNamespace(), engine=engine
    )

    with pytest.raises(ServiceError):
        await svc.run_refresh()
