"""Nikkei225Saver 単体テスト."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.data_synchronization.market_data.nikkei225.saver import Nikkei225Saver

# ── save — 空リスト ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_empty_list_returns_zero():
    """空リストを渡すと 0 が返り commit も呼ばれないこと."""
    session = AsyncMock()
    saver = Nikkei225Saver(session)

    result = await saver.save([])

    assert result == 0
    session.commit.assert_not_called()


# ── save — 正常フロー ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_calls_upsert_bulk_and_commit():
    """`save` が repository.upsert_bulk を呼び commit すること."""
    session = AsyncMock()
    saver = Nikkei225Saver(session)
    saver.repository = AsyncMock()
    saver.repository.upsert_bulk = AsyncMock(return_value=3)

    records = [{"dummy": i} for i in range(3)]
    result = await saver.save(records)

    assert result == 3
    saver.repository.upsert_bulk.assert_called_once_with(records)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_returns_upsert_bulk_count():
    """`upsert_bulk` の戻り値がそのまま返ること."""
    session = AsyncMock()
    saver = Nikkei225Saver(session)
    saver.repository = AsyncMock()
    saver.repository.upsert_bulk = AsyncMock(return_value=10)

    result = await saver.save([{"x": i} for i in range(10)])

    assert result == 10


# ── save — 例外・ロールバック ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_rollback_on_exception():
    """`upsert_bulk` が例外を投げたとき rollback されて例外が再送出されること."""
    session = AsyncMock()
    saver = Nikkei225Saver(session)
    saver.repository = AsyncMock()
    saver.repository.upsert_bulk = AsyncMock(side_effect=RuntimeError("DB error"))

    with pytest.raises(RuntimeError, match="DB error"):
        await saver.save([{"dummy": "data"}])

    session.rollback.assert_called_once()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_save_does_not_commit_after_rollback():
    """例外発生時に commit が呼ばれないこと（ロールバック確認）."""
    session = AsyncMock()
    saver = Nikkei225Saver(session)
    saver.repository = AsyncMock()
    saver.repository.upsert_bulk = AsyncMock(side_effect=ValueError("bad data"))

    with pytest.raises(ValueError):
        await saver.save([{"key": "value"}])

    session.commit.assert_not_called()
