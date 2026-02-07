"""`BatchExecutionDetailsRepository` の単体テスト集."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.repositories.batch_execution_details_repository import BatchExecutionDetailsRepository


@pytest.mark.asyncio
async def test_init_creates_instance_and_calls_add():
    """init がインスタンスを作成し session.add を呼ぶことを検証します."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionDetailsRepository(session)

    instance = await repo.init(1, "1d", total_stocks=100)

    session.add.assert_called()
    assert getattr(instance, "batch_execution_id") == 1
    assert getattr(instance, "total_stocks") == 100


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
async def test_inc_increments_existing_record_and_flushes():
    """既存レコードの processed_stocks が増加し flush が呼ばれることを検証します."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionDetailsRepository(session)

    dummy = SimpleNamespace(id=1, batch_execution_id=1, interval="1d", processed_stocks=2)
    session.execute = AsyncMock(return_value=_MockResult(single=dummy))

    updated = await repo.inc(1, "1d", count=3)

    assert updated is not None
    assert updated.processed_stocks == 5
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_set_status_updates_and_flushes():
    """set_status がレコードを更新し flush を呼ぶことを検証します."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    repo = BatchExecutionDetailsRepository(session)

    dummy = SimpleNamespace(id=2, batch_execution_id=2, interval="1h", status="pending")
    session.execute = AsyncMock(return_value=_MockResult(single=dummy))

    res = await repo.set_status(2, "1h", "running")

    assert res is not None
    assert res.status == "running"
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_get_progress_returns_list():
    """get_progress が進捗リストを返すことを検証します."""
    session = AsyncMock()
    repo = BatchExecutionDetailsRepository(session)

    d1 = SimpleNamespace(id=1, batch_execution_id=3, interval="1d")
    d2 = SimpleNamespace(id=2, batch_execution_id=3, interval="1h")
    session.execute = AsyncMock(return_value=_MockResult(items=[d1, d2]))

    res = await repo.get_progress(3)

    assert isinstance(res, list)
    assert len(res) == 2
