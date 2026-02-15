"""Unit tests for EdinetStockDividendRepository."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.edinet import EdinetStockDividend
from app.repositories.edinet_stock_dividend_repository import EdinetStockDividendRepository


@pytest.mark.asyncio
async def test_upsert_calls_session_and_returns_model():
    """upsert がセッションを呼び出し、モデルを返すことを確認する."""
    dummy = EdinetStockDividend(
        doc_id="D1",
        sec_code="7203",
        submission_date=date(2024, 4, 1),
        period_end_date=date(2024, 3, 31),
        fiscal_year=2024,
        report_type="annual",
        dividend_actual=12.34,
    )

    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()

    repo = EdinetStockDividendRepository(mock_session)

    # patch find_by_period to return our dummy after upsert
    repo.find_by_period = AsyncMock(return_value=dummy)

    data = {
        "doc_id": "D1",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
    }
    res = await repo.upsert(data)

    assert res is dummy
    mock_session.execute.assert_awaited()
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_upsert_with_empty_data_raises():
    """空データで upsert が ValueError を発生させることを確認する."""
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()

    repo = EdinetStockDividendRepository(mock_session)

    with pytest.raises(ValueError):
        await repo.upsert({})


@pytest.mark.asyncio
async def test_find_latest_by_sec_code_returns_model():
    """sec_code から最新のモデルを取得できることを確認する."""
    dummy = EdinetStockDividend(
        doc_id="D1",
        sec_code="7203",
        submission_date=date(2024, 4, 1),
        period_end_date=date(2024, 3, 31),
        fiscal_year=2024,
        report_type="annual",
        dividend_actual=12.34,
    )

    result_obj = MagicMock()
    result_obj.scalar_one_or_none = lambda: dummy

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=result_obj)

    repo = EdinetStockDividendRepository(mock_session)

    res = await repo.find_latest_by_sec_code("7203")
    assert res is dummy
