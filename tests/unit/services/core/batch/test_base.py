"""Unit tests for `BaseBatchRunner` utilities."""

from types import SimpleNamespace

import pytest

from app.services.core.batch.base import BaseBatchRunner


def test_chunk_iter_splits_correctly():
    """chunk_iter が指定サイズでリストを分割することを検証する."""
    items = list(range(7))
    chunks = list(BaseBatchRunner.chunk_iter(items, 3))
    assert chunks == [[0, 1, 2], [3, 4, 5], [6]]


@pytest.mark.asyncio
async def test_update_ctx_progress_handles_various_updaters():
    """_update_ctx_progress が同期/非同期の updater を正しく扱うことを検証する."""
    runner = BaseBatchRunner()

    # no ctx -> should be no-op
    await runner._update_ctx_progress(None, processed=1)

    # sync updater
    called = {}

    def sync_updater(**kwargs):
        called["sync"] = kwargs

    ctx_sync = SimpleNamespace(update_progress=sync_updater)
    await runner._update_ctx_progress(ctx_sync, processed=2)
    assert called["sync"]["processed"] == 2

    # async updater
    async def async_updater(**kwargs):
        called["async"] = kwargs

    ctx_async = SimpleNamespace(update_progress=async_updater)
    await runner._update_ctx_progress(ctx_async, processed=3)
    assert called["async"]["processed"] == 3

    # updater that raises should be swallowed
    def bad_updater(**kwargs):
        raise RuntimeError("boom")

    ctx_bad = SimpleNamespace(update_progress=bad_updater)
    await runner._update_ctx_progress(ctx_bad, processed=4)
