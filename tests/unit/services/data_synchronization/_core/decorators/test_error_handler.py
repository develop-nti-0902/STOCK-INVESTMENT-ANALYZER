"""Unit tests for core decorators error handling."""

import pytest

from app.exceptions import ServiceError
from app.services.data_synchronization._core.decorators.error_handler import handle_service_error


def test_handle_service_error_sync_raises():
    """`handle_service_error` が例外を ServiceError に変換して再送出することを検証する."""

    @handle_service_error(reraise=True)
    def f():
        raise ValueError("boom")

    with pytest.raises(ServiceError):
        f()


def test_handle_service_error_sync_returns_none_when_reraise_false():
    """`handle_service_error(reraise=False)` が例外発生時に None を返すことを確認する."""

    @handle_service_error(reraise=False)
    def f():
        raise ValueError("boom")

    assert f() is None
