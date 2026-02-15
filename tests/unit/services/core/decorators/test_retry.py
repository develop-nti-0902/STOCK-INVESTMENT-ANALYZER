"""Unit tests for retry decorator."""

import pytest

from app.services.core.decorators.retry import retry, retry_on_error


def test_retry_decorator_retries_on_exception(monkeypatch):
    """`retry` デコレータが例外発生時に指定回数リトライすることを確認する."""
    calls = {"c": 0}

    def f():
        calls["c"] += 1
        if calls["c"] < 3:
            raise ValueError("try")
        return True

    wrapped = retry(retries=3)(f)
    assert wrapped() is True


def test_retry_on_error_sync_raises_after_retries():
    """`retry_on_error` がリトライ後に例外を送出することを確認する."""

    @retry_on_error(max_retries=1, delay=0)
    def f():
        raise ValueError("fail")

    with pytest.raises(ValueError):
        f()
