"""Unit tests for `app.api.v1.stock_price` endpoints."""

from datetime import datetime, timezone

import pytest

from app.api.v1 import stock_price as stock_price_module
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.exceptions.validation import FieldValidationError


class DummyDB:
    """A minimal dummy DB object that supports commit/rollback for tests."""

    def __init__(self):
        """Initialize DummyDB with commit/rollback tracking flags."""
        self.committed = False
        self.rolled_back = False

    async def commit(self):
        """Simulate commit by marking `committed` True."""
        self.committed = True

    async def rollback(self):
        """Simulate rollback by marking `rolled_back` True."""
        self.rolled_back = True


class FakeService:
    """Fake service used by tests to simulate data retrieval and deletion."""

    def __init__(
        self, *, rows=None, deleted_count: int | None = None, error: Exception | None = None
    ):
        """Initialize FakeService with configurable rows, deleted_count and error."""
        self._rows = rows
        self._deleted_count = deleted_count
        self._error = error

    async def get_stock_data_from_db(self, db, symbol, timeframe, start, end, limit, offset):
        """Return configured rows or raise configured errors."""
        if isinstance(self._error, FieldValidationError) or isinstance(
            self._error, RecordNotFoundError
        ):
            raise self._error
        if self._rows is None:
            raise RecordNotFoundError(message=f"No data found for symbol '{symbol}'")
        return self._rows

    async def delete_all_for_timeframe(self, db, timeframe):
        """Delete all and either commit or raise as configured."""
        if isinstance(self._error, FieldValidationError):
            raise self._error
        if isinstance(self._error, Exception):
            await db.rollback()
            raise ServiceError(message=str(self._error))
        if self._deleted_count is None:
            return 0
        await db.commit()
        return self._deleted_count


@pytest.mark.asyncio
async def test_get_stock_price_invalid_start_format_raises_400():
    """Verify invalid start date format raises FieldValidationError."""
    with pytest.raises(FieldValidationError) as exc:
        await stock_price_module.get_stock_price_data(
            symbol="7203",
            timeframe="1d",
            start="not-a-date",
            end=None,
            limit=10,
            offset=0,
            service=FakeService(rows=[]),
            db=None,
        )

    assert exc.value.status_code == 400
    assert "Invalid start date format" in exc.value.message


@pytest.mark.asyncio
async def test_get_stock_price_invalid_timeframe_raises_400():
    """Verify invalid timeframe format raises FieldValidationError."""
    svc = FakeService(rows=[], error=FieldValidationError(message="Invalid timeframe: 2h"))

    with pytest.raises(FieldValidationError) as exc:
        await stock_price_module.get_stock_price_data(
            symbol="7203",
            timeframe="2h",
            start=None,
            end=None,
            limit=10,
            offset=0,
            service=svc,
            db=None,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_stock_price_no_results_raises_404():
    """Verify no results causes RecordNotFoundError."""
    svc = FakeService(rows=None)

    with pytest.raises(RecordNotFoundError) as exc:
        await stock_price_module.get_stock_price_data(
            symbol="9999",
            timeframe="1d",
            start=None,
            end=None,
            limit=10,
            offset=0,
            service=svc,
            db=None,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_stock_price_success_returns_data():
    """Verify successful retrieval returns properly shaped response."""
    now = datetime.now(timezone.utc)
    rows = [
        {
            "symbol": "7203",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 105.0,
            "adj_close": 104.5,
            "volume": 1000,
            "timestamp": now,
        },
        {
            "symbol": "7203",
            "open": 200.0,
            "high": 210.0,
            "low": 195.0,
            "close": 205.0,
            "volume": 2000,
            # no adj_close on purpose
        },
    ]

    svc = FakeService(rows=rows)

    resp = await stock_price_module.get_stock_price_data(
        symbol="7203",
        timeframe="1d",
        start=None,
        end=None,
        limit=10,
        offset=0,
        service=svc,
        db=None,
    )

    assert resp.symbol == "7203"
    assert resp.count == 2
    assert resp.data[0].adj_close == 104.5
    assert resp.data[1].adj_close is None


@pytest.mark.asyncio
async def test_delete_all_success_commits_and_returns_count():
    """Verify delete_all commits and returns deleted count on success."""
    db = DummyDB()
    svc = FakeService(deleted_count=5)

    resp = await stock_price_module.delete_all_stock_price_data(
        timeframe="1d",
        service=svc,
        db=db,
    )

    assert resp.deleted_count == 5
    assert db.committed is True


@pytest.mark.asyncio
async def test_delete_all_invalid_timeframe_raises_400():
    """Verify invalid timeframe for delete_all raises FieldValidationError."""
    db = DummyDB()
    svc = FakeService(error=FieldValidationError(message="Invalid timeframe: 2h"))

    with pytest.raises(FieldValidationError):
        await stock_price_module.delete_all_stock_price_data(
            timeframe="2h",
            service=svc,
            db=db,
        )


@pytest.mark.asyncio
async def test_delete_all_failure_rolls_back_and_raises():
    """Verify delete_all rolls back and raises on service failure."""
    db = DummyDB()
    svc = FakeService(error=RuntimeError("boom"))

    with pytest.raises(ServiceError):
        await stock_price_module.delete_all_stock_price_data(
            timeframe="1d",
            service=svc,
            db=db,
        )

    assert db.rolled_back is True
