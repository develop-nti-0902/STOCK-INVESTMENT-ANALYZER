from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.batch.batch_execution_service import (
    BatchExecutionContext,
    BatchExecutionService,
)


@pytest.mark.asyncio
async def test_context_success_calls_mark_completed():
    repo = AsyncMock()
    # fake job instance
    job = SimpleNamespace(
        id=1, processed_stocks=10, successful_stocks=10, failed_stocks=0
    )
    repo.create_job.return_value = job
    repo.update_status.return_value = job
    repo.get.return_value = job
    repo.mark_completed.return_value = job

    service = BatchExecutionService(repository=repo)

    async with BatchExecutionContext(service, job_type="test") as ctx:
        await ctx.update_progress(processed=5)

    repo.create_job.assert_awaited()
    repo.update_status.assert_awaited()
    repo.mark_completed.assert_awaited()


@pytest.mark.asyncio
async def test_context_failure_calls_fail_job():
    repo = AsyncMock()
    job = SimpleNamespace(
        id=2, processed_stocks=0, successful_stocks=0, failed_stocks=0
    )
    repo.create_job.return_value = job
    repo.update_status.return_value = job
    repo.get.return_value = job
    repo.update.return_value = job

    service = BatchExecutionService(repository=repo)

    with pytest.raises(RuntimeError):

        async def _run():
            async with BatchExecutionContext(service, job_type="test"):
                raise RuntimeError("boom")

        await _run()

    repo.create_job.assert_awaited()
    repo.update_status.assert_awaited()
    # fail_job uses repository.update, so ensure update was awaited
    repo.update.assert_awaited()
