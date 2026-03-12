"""Unit tests for EdinetStockDividendRepository."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.edinet import EdinetStockDividend
from app.repositories.market_data.edinet.edinet_stock_dividend_repository import (
    EdinetStockDividendRepository,
)


@pytest.mark.asyncio
async def test_upsert_calls_session_and_returns_model():
    """upsert がセッションを呼び出し、モデルを返すことを確認する."""
    mock_session = MagicMock()
    mock_session.flush = AsyncMock()

    # Mock the result object with first() for RETURNING clause
    mock_row = MagicMock()
    mock_row._mapping = {
        "edinet_document_id": 1,
        "period_end_date": date(2024, 3, 31),
        "fiscal_year": 2024,
        "dividend_actual": 12.34,
    }

    mock_result = MagicMock()
    mock_result.first.return_value = mock_row

    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = EdinetStockDividendRepository(mock_session)

    data = {
        "edinet_document_id": 1,
        "period_end_date": date(2024, 3, 31),
    }
    res = await repo.upsert(data)

    assert res is not None
    assert res.edinet_document_id == 1
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
        edinet_document_id=1,
        period_end_date=date(2024, 3, 31),
        fiscal_year=2024,
        dividend_actual=12.34,
    )

    result_obj = MagicMock()
    result_obj.scalar_one_or_none = lambda: dummy

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=result_obj)

    repo = EdinetStockDividendRepository(mock_session)

    res = await repo.find_latest_by_sec_code("7203")
    assert res is dummy


@pytest.mark.asyncio
async def test_save_batch_upsert_success():
    """save_batch_upsert がバッチ処理を実行し、モデルリストを返すことを確認する."""
    mock_session = MagicMock()
    mock_session.flush = AsyncMock()

    # Mock the result object with fetchall() for RETURNING clause
    mock_rows = [
        MagicMock(
            _mapping={
                "edinet_document_id": 1,
                "period_end_date": date(2024, 3, 31),
                "fiscal_year": 2024,
                "dividend_actual": 12.34,
            }
        ),
        MagicMock(
            _mapping={
                "edinet_document_id": 2,
                "period_end_date": date(2024, 3, 31),
                "fiscal_year": 2024,
                "dividend_actual": 11.50,
            }
        ),
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows

    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = EdinetStockDividendRepository(mock_session)

    data_list = [
        {
            "edinet_document_id": 1,
            "period_end_date": date(2024, 3, 31),
        },
        {
            "edinet_document_id": 2,
            "period_end_date": date(2024, 3, 31),
        },
    ]

    res = await repo.save_batch(data_list)

    assert len(res) == 2
    assert res[0].edinet_document_id == 1
    assert res[1].edinet_document_id == 2
    mock_session.execute.assert_awaited()
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_save_batch_upsert_empty_list():
    """save_batch_upsert で空リストの場合、空リストを返すことを確認する."""
    mock_session = MagicMock()
    repo = EdinetStockDividendRepository(mock_session)

    res = await repo.save_batch([])
    assert res == []


@pytest.mark.asyncio
async def test_save_batch_upsert_none_raises():
    """save_batch_upsert で None の場合に ValueError を発生させることを確認する."""
    mock_session = MagicMock()
    repo = EdinetStockDividendRepository(mock_session)

    with pytest.raises(ValueError, match="data_list is required for save_batch_upsert"):
        await repo.save_batch(None)
