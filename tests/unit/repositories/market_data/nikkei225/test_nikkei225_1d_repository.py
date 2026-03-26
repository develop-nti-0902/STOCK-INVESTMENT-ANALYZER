"""Nikkei2251dRepository 単体テスト."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.market_data.nikkei225 import Nikkei2251dRepository

# ── テスト用定数 ──────────────────────────────────────────────────────────

_SAMPLE_RECORD = {
    "timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc),
    "open": Decimal("35000.00"),
    "high": Decimal("35100.00"),
    "low": Decimal("34900.00"),
    "close": Decimal("35050.00"),
    "adj_close": None,
    "volume": 1_000_000,
}


# ── upsert_bulk ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_bulk_empty_returns_zero():
    """空リストで upsert_bulk を呼ぶと 0 が返ること."""
    session = AsyncMock()
    repo = Nikkei2251dRepository(session)

    result = await repo.upsert_bulk([])

    assert result == 0
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_bulk_calls_execute_and_flush():
    """`upsert_bulk` が execute・flush を呼び rowcount を返すこと."""
    mock_result = MagicMock()
    mock_result.rowcount = 1
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()

    repo = Nikkei2251dRepository(session)
    result = await repo.upsert_bulk([_SAMPLE_RECORD])

    assert result == 1
    session.execute.assert_called_once()
    session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_bulk_multiple_records():
    """複数レコードで rowcount がそのまま返ること."""
    mock_result = MagicMock()
    mock_result.rowcount = 3
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()

    repo = Nikkei2251dRepository(session)
    records = [_SAMPLE_RECORD.copy() for _ in range(3)]
    result = await repo.upsert_bulk(records)

    assert result == 3


# ── upsert_single ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_upsert_single_returns_rowcount_and_operation():
    """`upsert_single` が rowcount と operation を含む dict を返すこと."""
    mock_result = MagicMock()
    mock_result.rowcount = 1
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = Nikkei2251dRepository(session)
    result = await repo.upsert_single(_SAMPLE_RECORD)

    assert result["rowcount"] == 1
    assert result["operation"] == "upsert"
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_single_calls_execute():
    """`upsert_single` が必ず execute を呼ぶこと."""
    mock_result = MagicMock()
    mock_result.rowcount = 0
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = Nikkei2251dRepository(session)
    await repo.upsert_single(_SAMPLE_RECORD)

    session.execute.assert_called_once()
