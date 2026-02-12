import pytest
from fastapi import HTTPException

from app.api.v1.edinet import process_date_range


class FakeService:
    def __init__(self, result=None, exc: Exception | None = None):
        self._result = result
        self._exc = exc

    async def process_date_range(self, *args, **kwargs):
        if self._exc:
            raise self._exc
        return self._result


@pytest.mark.asyncio
async def test_process_date_range_success():
    svc = FakeService(result={"ok": True})
    res = await process_date_range(
        start_date="2020-01-01",
        end_date="2020-01-31",
        service=svc,
        db=None,
    )
    assert res == {"ok": True}


@pytest.mark.asyncio
async def test_process_date_range_raises_http_exception_on_error():
    svc = FakeService(exc=RuntimeError("boom"))
    with pytest.raises(HTTPException):
        await process_date_range(
            start_date="2020-01-01",
            end_date="2020-01-31",
            service=svc,
            db=None,
        )
