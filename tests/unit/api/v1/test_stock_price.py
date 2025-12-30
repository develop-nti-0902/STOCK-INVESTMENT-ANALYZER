from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import stock_price as stock_price_module


class FakeRepoClass:
    def __init__(self, session=None, results=None, delete_count=0):
        self._results = results or []
        self._delete_count = delete_count

    async def get_by_symbol_and_range(self, symbol, start, end, limit, offset):
        return self._results

    async def delete_all(self):
        return self._delete_count


class DummyDB:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_get_stock_price_invalid_timeframe_raises_400():
    # Arrange
    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await stock_price_module.get_stock_price_data(
            symbol="7203",
            timeframe="2h",
            start=None,
            end=None,
            limit=10,
            offset=0,
            db=None,
        )

    assert exc.value.status_code == 400
    assert "Invalid timeframe" in exc.value.detail


@pytest.mark.asyncio
async def test_get_stock_price_invalid_start_format_raises_400(monkeypatch):
    # Arrange: map timeframe to fake repo
    monkeypatch.setitem(
        stock_price_module.TIMEFRAME_REPOSITORY_MAP, "1d", FakeRepoClass
    )

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await stock_price_module.get_stock_price_data(
            symbol="7203",
            timeframe="1d",
            start="bad-date",
            end=None,
            limit=10,
            offset=0,
            db=None,
        )

    assert exc.value.status_code == 400
    assert "Invalid start date format" in exc.value.detail


@pytest.mark.asyncio
async def test_get_stock_price_no_results_raises_404(monkeypatch):
    # Arrange: mapping returns repo that yields empty results
    def _fake_repo_empty(session):
        return FakeRepoClass(results=[])

    monkeypatch.setitem(
        stock_price_module.TIMEFRAME_REPOSITORY_MAP,
        "1d",
        _fake_repo_empty,
    )

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await stock_price_module.get_stock_price_data(
            symbol="9999",
            timeframe="1d",
            start=None,
            end=None,
            limit=10,
            offset=0,
            db=None,
        )

    assert exc.value.status_code == 404
    assert "No data found for symbol '9999'" in exc.value.detail


@pytest.mark.asyncio
async def test_get_stock_price_success_with_timestamp_and_adj_close(
    monkeypatch,
):
    # Arrange: create fake rows with fields expected by the endpoint
    row1 = SimpleNamespace(
        symbol="7203",
        open=100,
        high=110,
        low=95,
        close=105,
        volume=1000,
        adj_close=104.5,
        timestamp=datetime.now(timezone.utc),
    )
    row2 = SimpleNamespace(
        symbol="7203",
        open=200,
        high=210,
        low=195,
        close=205,
        volume=2000,
        trade_date=datetime.now(timezone.utc).date(),
    )
    fake_repo = FakeRepoClass(results=[row1, row2])

    def _fake_repo(session):
        return fake_repo

    monkeypatch.setitem(
        stock_price_module.TIMEFRAME_REPOSITORY_MAP,
        "1d",
        _fake_repo,
    )

    # Act
    resp = await stock_price_module.get_stock_price_data(
        symbol="7203",
        timeframe="1d",
        start=None,
        end=None,
        limit=10,
        offset=0,
        db=None,
    )

    # Assert
    assert resp.symbol == "7203"
    assert resp.count == 2
    assert resp.data[0].adj_close == 104.5
    assert resp.data[1].trade_date is not None


@pytest.mark.asyncio
async def test_delete_all_stock_price_data_success(monkeypatch):
    # Arrange
    def fake_repo_factory(session):
        return FakeRepoClass(delete_count=5)

    monkeypatch.setitem(
        stock_price_module.TIMEFRAME_REPOSITORY_MAP, "1d", fake_repo_factory
    )
    db = DummyDB()

    # Act
    resp = await stock_price_module.delete_all_stock_price_data(
        timeframe="1d",
        db=db,
    )

    # Assert
    assert resp.deleted_count == 5
    assert db.committed is True


@pytest.mark.asyncio
async def test_delete_all_stock_price_data_invalid_timeframe_raises_400():
    # Arrange
    db = DummyDB()

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await stock_price_module.delete_all_stock_price_data(
            timeframe="2h",
            db=db,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_all_stock_price_data_failure_rolls_back(monkeypatch):
    # Arrange: make repo.delete_all raise
    class ExplodingRepo(FakeRepoClass):
        async def delete_all(self):
            raise RuntimeError("boom")

    monkeypatch.setitem(
        stock_price_module.TIMEFRAME_REPOSITORY_MAP,
        "1d",
        lambda session: ExplodingRepo(),
    )
    db = DummyDB()

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        await stock_price_module.delete_all_stock_price_data(
            timeframe="1d", db=db
        )

    assert exc.value.status_code == 500
    assert db.rolled_back is True
