from types import SimpleNamespace

import pytest

from app.exceptions.business import ServiceError
from app.services.views.refresh_service import LatestStocksRefreshService


@pytest.mark.asyncio
async def test_enqueue_refresh_returns_job_id() -> None:
    executed = []

    class AsyncConn:
        async def execute(self, stmt):
            executed.append(str(stmt))

        async def commit(self):
            pass

    class AsyncConnCtx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class AsyncEngine:
        def connect(self):
            return AsyncConnCtx(AsyncConn())

    class FakeBatch:
        async def create_job(self, job_type: str):
            return SimpleNamespace(id=123)

        async def start_job(self, job_id: int):
            pass

        async def complete_job(
            self, job_id: int, success_count: int, failed_count: int
        ):
            pass

    engine = AsyncEngine()
    svc = LatestStocksRefreshService(batch_service=FakeBatch(), engine=engine)
    jid = await svc.enqueue_refresh()

    assert jid == 123
    # run_refresh が実行されたことを確認
    assert any("REFRESH MATERIALIZED VIEW" in s for s in executed)


@pytest.mark.asyncio
async def test_run_refresh_executes_refresh_sql() -> None:
    executed = []

    class AsyncConn:
        async def execute(self, stmt):
            executed.append(str(stmt))

        async def commit(self):
            pass

    class AsyncConnCtx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class AsyncEngine:
        def connect(self):
            return AsyncConnCtx(AsyncConn())

    engine = AsyncEngine()
    svc = LatestStocksRefreshService(
        batch_service=SimpleNamespace(), engine=engine
    )

    await svc.run_refresh()

    assert any("REFRESH MATERIALIZED VIEW" in s for s in executed)


@pytest.mark.asyncio
async def test_run_refresh_raises_service_error_on_execute_failure() -> None:
    class FailingConn:
        async def execute(self, stmt):
            raise RuntimeError("boom")

        async def commit(self):
            pass

    class AsyncConnCtx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class AsyncEngine:
        def connect(self):
            return AsyncConnCtx(FailingConn())

    engine = AsyncEngine()
    svc = LatestStocksRefreshService(
        batch_service=SimpleNamespace(), engine=engine
    )

    with pytest.raises(ServiceError):
        await svc.run_refresh()


@pytest.mark.asyncio
async def test_enqueue_refresh_fails_job_on_error() -> None:
    """enqueue_refresh でエラーが発生した場合、fail_job が呼ばれることを確認"""
    failed_job_id = None
    error_msg = None

    class FailingConn:
        async def execute(self, stmt):
            raise RuntimeError("database error")

        async def commit(self):
            pass

    class AsyncConnCtx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class AsyncEngine:
        def connect(self):
            return AsyncConnCtx(FailingConn())

    class FakeBatch:
        async def create_job(self, job_type: str):
            return SimpleNamespace(id=456)

        async def start_job(self, job_id: int):
            pass

        async def complete_job(
            self, job_id: int, success_count: int, failed_count: int
        ):
            pass

        async def fail_job(self, job_id: int, error_message: str):
            nonlocal failed_job_id, error_msg
            failed_job_id = job_id
            error_msg = error_message

    engine = AsyncEngine()
    svc = LatestStocksRefreshService(batch_service=FakeBatch(), engine=engine)

    with pytest.raises(ServiceError):
        await svc.enqueue_refresh()

    assert failed_job_id == 456
    assert "database error" in error_msg
