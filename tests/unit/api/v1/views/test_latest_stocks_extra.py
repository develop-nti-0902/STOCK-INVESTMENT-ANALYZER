"""追加の unit tests for app.api.v1.views.latest_stocks

場所: tests/unit/api/v1/views1
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1.views import latest_stocks as ls_module
from app.exceptions.business import ServiceError


class FakeLatestService:
    def __init__(self, *, result=None, raise_exc: Exception | None = None):
        self._result = result
        self._raise = raise_exc

    async def get_latest_stock(self, symbol: str):
        if self._raise:
            raise self._raise
        return self._result


@pytest.mark.asyncio
async def test_get_latest_stock_success():
    now = datetime.now(timezone.utc)
    fake = SimpleNamespace(
        id=11,
        symbol="7203",
        timestamp=now,
        open_price=100.0,
        high=110.0,
        low=95.0,
        close=105.0,
        volume=1234,
        adj_close=104.5,
    )

    service = FakeLatestService(result=fake)

    res = await ls_module.get_latest_stock(symbol="7203", service=service)

    assert res is fake
    assert res.id == 11
    assert res.symbol == "7203"


@pytest.mark.asyncio
async def test_get_latest_stock_not_found_raises_404():
    service = FakeLatestService(
        raise_exc=ServiceError(message="Not found for symbol")
    )

    with pytest.raises(HTTPException) as exc:
        await ls_module.get_latest_stock(symbol="XXXX", service=service)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_latest_stock_other_service_error_raises_500():
    service = FakeLatestService(
        raise_exc=ServiceError(message="something bad")
    )

    with pytest.raises(HTTPException) as exc:
        await ls_module.get_latest_stock(symbol="7203", service=service)

    assert exc.value.status_code == 500
