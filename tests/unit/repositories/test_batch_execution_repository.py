from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)


@pytest.mark.asyncio
async def test_create_job_calls_session_and_returns_instance():
    # Arrange
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionRepository(session)

    # Act
    instance = await repo.create_job("daily_sync")

    # Assert
    session.add.assert_called()
    assert getattr(instance, "batch_type") == "daily_sync"


class _MockResult:
    def __init__(self, items=None, single=None):
        self._items = items or []
        self._single = single

    def scalars(self):
        class _S:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _S(self._items)

    def scalar_one_or_none(self):
        return self._single


@pytest.mark.asyncio
async def test_get_by_job_type_returns_list():
    # Arrange
    session = AsyncMock()
    repo = BatchExecutionRepository(session)

    dummy = SimpleNamespace(id=1, batch_type="daily", status="pending")
    session.execute = AsyncMock(return_value=_MockResult(items=[dummy]))

    # Act
    res = await repo.get_by_job_type("daily")

    # Assert
    session.execute.assert_called()
    assert isinstance(res, list)
    assert res[0].batch_type == "daily"


@pytest.mark.asyncio
async def test_get_by_job_type_empty_returns_empty_list():
    # Arrange
    session = AsyncMock()
    repo = BatchExecutionRepository(session)
    session.execute = AsyncMock(return_value=_MockResult(items=[]))

    # Act
    res = await repo.get_by_job_type("none")

    # Assert
    assert res == []


@pytest.mark.asyncio
async def test_update_status_updates_and_commits():
    # Arrange
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionRepository(session)

    dummy = SimpleNamespace(id=10, status="pending")
    session.execute = AsyncMock(return_value=_MockResult(single=dummy))

    # Act
    updated = await repo.update_status(10, "running")

    # Assert: flush が呼ばれること（commitはService層で実施）
    assert updated is not None
    assert updated.status == "running"
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_update_status_not_found_returns_none():
    # Arrange
    session = AsyncMock()
    repo = BatchExecutionRepository(session)
    session.execute = AsyncMock(return_value=_MockResult(single=None))

    # Act
    updated = await repo.update_status(999, "running")

    # Assert
    assert updated is None


@pytest.mark.asyncio
async def test_mark_completed_sets_counts_and_end_time():
    # Arrange
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionRepository(session)

    dummy = SimpleNamespace(
        id=5,
        status="running",
        successful_stocks=0,
        failed_stocks=0,
        processed_stocks=0,
        end_time=None,
    )
    session.execute = AsyncMock(return_value=_MockResult(single=dummy))

    # Act
    res = await repo.mark_completed(5, success_count=3, failed_count=1)

    # Assert
    assert res is not None
    assert res.status == "completed"
    assert res.successful_stocks == 3
    assert res.failed_stocks == 1
    assert res.processed_stocks == 4
    assert res.end_time is not None


@pytest.mark.asyncio
async def test_mark_completed_not_found_returns_none():
    # Arrange
    session = AsyncMock()
    repo = BatchExecutionRepository(session)
    session.execute = AsyncMock(return_value=_MockResult(single=None))

    # Act
    res = await repo.mark_completed(123, success_count=0, failed_count=0)

    # Assert
    assert res is None


@pytest.mark.asyncio
async def test_get_recent_returns_list():
    # Arrange
    session = AsyncMock()
    repo = BatchExecutionRepository(session)
    d1 = SimpleNamespace(id=1, start_time=1)
    d2 = SimpleNamespace(id=2, start_time=2)
    session.execute = AsyncMock(return_value=_MockResult(items=[d2, d1]))

    # Act
    res = await repo.get_recent(limit=2)

    # Assert
    assert isinstance(res, list)
    assert len(res) == 2


@pytest.mark.asyncio
async def test_create_job_rollback_on_failure():
    # Arrange
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # make add raise
    async def _raise(*args, **kwargs):
        raise SQLAlchemyError("boom")

    session.add = AsyncMock(side_effect=_raise)
    repo = BatchExecutionRepository(session)

    # Act / Assert: 例外が伝播すること（rollbackはService層で実施）
    with pytest.raises(SQLAlchemyError):
        await repo.create_job("fail_job")

    # Repository層ではrollbackを呼ばない


@pytest.mark.asyncio
async def test_update_progress_updates_fields_and_flushes():
    # Arrange
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionRepository(session)

    dummy = SimpleNamespace(
        id=20,
        processed_stocks=0,
        successful_stocks=0,
        failed_stocks=0,
        total_stocks=0,
    )
    session.execute = AsyncMock(return_value=_MockResult(single=dummy))

    # Act
    updated = await repo.update_progress(
        20,
        {"processed": 5, "successful": 4, "failed": 1, "total": 100},
    )

    # Assert
    assert updated is not None
    assert updated.processed_stocks == 5
    assert updated.successful_stocks == 4
    assert updated.failed_stocks == 1
    assert updated.total_stocks == 100
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_get_running_jobs_returns_list():
    # Arrange
    session = AsyncMock()
    repo = BatchExecutionRepository(session)

    d1 = SimpleNamespace(id=1, status="running")
    d2 = SimpleNamespace(id=2, status="running")
    session.execute = AsyncMock(return_value=_MockResult(items=[d1, d2]))

    # Act
    res = await repo.get_running_jobs()

    # Assert
    session.execute.assert_called()
    assert isinstance(res, list)
    assert len(res) == 2


@pytest.mark.asyncio
async def test_cancel_job_sets_status_and_end_time_and_flush():
    # Arrange
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionRepository(session)

    dummy = SimpleNamespace(id=30, status="running", end_time=None)
    session.execute = AsyncMock(return_value=_MockResult(single=dummy))

    # Act
    res = await repo.cancel_job(30)

    # Assert
    assert res is not None
    assert res.status == "cancelled"
    assert res.end_time is not None
    session.flush.assert_awaited()
