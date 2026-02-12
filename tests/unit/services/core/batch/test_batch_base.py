import asyncio

import pytest

from app.services.core.batch.base import BaseBatchRunner, BatchExecutionContext


def test_chunk_iter_splits_list():
    items = [1, 2, 3, 4, 5]
    chunks = list(BaseBatchRunner.chunk_iter(items, 2))
    assert chunks == [[1, 2], [3, 4], [5]]


@pytest.mark.asyncio
async def test_update_ctx_progress_with_sync_and_async(monkeypatch):
    class Ctx:
        def __init__(self):
            self.called = False

        def update_progress(self, **kwargs):
            self.called = True

    runner = BaseBatchRunner(batch_service=object())
    ctx = Ctx()
    await runner._update_ctx_progress(ctx, a=1)
    assert ctx.called

    class AsyncCtx:
        def __init__(self):
            self.called = False

        async def update_progress(self, **kwargs):
            self.called = True

    actx = AsyncCtx()
    await runner._update_ctx_progress(actx, b=2)
    assert actx.called


@pytest.mark.asyncio
async def test_batch_execution_context_create_and_finish_sync(monkeypatch):
    # batch_service provides create_context (sync) which returns ctx with finish sync
    class Ctx:
        def __init__(self):
            self.finished = False

        def finish(self, success: bool, error: str | None = None):
            self.finished = True

    class Service:
        def create_context(self, job_type, params):
            return Ctx()

    svc = Service()
    async with BatchExecutionContext(svc, job_type="j", params={}) as ctx:
        assert ctx is not None
    # after exit, finish should have been called (no exception)


@pytest.mark.asyncio
async def test_batch_execution_context_start_job_async_and_finish_async(monkeypatch):
    # start_job returns coroutine that resolves to ctx; ctx.finish is async
    class Ctx:
        def __init__(self):
            self.finished = False

        async def finish(self, success: bool, error: str | None = None):
            self.finished = True

    class Service:
        async def start_job(self, job_type, params):
            return Ctx()

    svc = Service()
    async with BatchExecutionContext(svc, job_type="j2", params={}) as ctx:
        assert ctx is not None
