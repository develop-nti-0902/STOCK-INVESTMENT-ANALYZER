"""Unit tests for views.latest_stocks endpoints."""

import pytest
from fastapi import HTTPException

from app.api.v1.views.latest_stocks import refresh_latest_stocks
from app.exceptions.business import ServiceError


class FakeService:
    """A tiny fake service used to simulate enqueue behavior."""

    def __init__(self, *, job_id: int = 123, raise_on: bool = False):
        """Initialize FakeService with optional job id and error flag."""
        self._job_id = job_id
        self._raise_on = raise_on

    async def enqueue_refresh(self):
        """Enqueue refresh or raise ServiceError when configured."""
        if self._raise_on:
            raise ServiceError(message="enqueue failed")
        return self._job_id


@pytest.mark.asyncio
async def test_refresh_latest_stocks_success():
    """Verify refresh_latest_stocks returns job id on success."""
    service = FakeService(job_id=999)

    resp = await refresh_latest_stocks(service=service)

    assert resp["job_id"] == 999


@pytest.mark.asyncio
async def test_refresh_latest_stocks_service_error_raises_http_exception():
    """Verify ServiceError is converted to HTTPException with 500 status."""
    service = FakeService(raise_on=True)

    with pytest.raises(HTTPException) as exc:
        await refresh_latest_stocks(service=service)

    assert exc.value.status_code == 500
