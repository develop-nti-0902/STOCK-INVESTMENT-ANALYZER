"""Tests for EdinetBalanceSheetSaver behavior and validation."""

from unittest.mock import AsyncMock

import pytest

from app.services.market_data.edinet.balance_sheet.saver import EdinetBalanceSheetSaver


@pytest.mark.asyncio
async def test_validate_data_success():
    """Return True when required fields are present in payload."""
    saver = EdinetBalanceSheetSaver(session=None)
    data = {
        "doc_id": "doc1",
        "sec_code": "7203",
        "submission_date": "2020-01-01",
        "period_end_date": "2019-12-31",
        "report_type": "annual",
    }

    assert await saver.validate_data(data) is True


@pytest.mark.asyncio
async def test_validate_data_missing_field_returns_false():
    """Return False when required fields are missing."""
    saver = EdinetBalanceSheetSaver(session=None)
    data = {"sec_code": "7203"}  # missing required fields

    assert await saver.validate_data(data) is False


@pytest.mark.asyncio
async def test_save_single_calls_repository_upsert_and_returns_result():
    """Delegate single save to repository upsert and return result."""
    saver = EdinetBalanceSheetSaver(session=None)

    mock_repo = AsyncMock()
    mock_repo.upsert = AsyncMock(return_value={"id": 1})
    saver.repository = mock_repo

    payload = {"doc_id": "doc1"}
    result = await saver.save_single(payload)

    mock_repo.upsert.assert_awaited_once_with(payload)
    assert result == {"id": 1}


@pytest.mark.asyncio
async def test_save_batch_counts_successful_and_raises_on_error():
    """Count successful upserts and propagate errors from repository."""
    saver = EdinetBalanceSheetSaver(session=None)

    # Successful path: upsert always succeeds
    mock_repo = AsyncMock()
    mock_repo.upsert = AsyncMock(return_value=None)
    saver.repository = mock_repo

    data_list = [{"doc_id": "a"}, {"doc_id": "b"}]
    saved_count = await saver.save_batch(data_list)
    assert saved_count == 2

    # Error path: second call raises
    mock_repo = AsyncMock()
    mock_repo.upsert = AsyncMock(side_effect=[None, RuntimeError("fail")])
    saver.repository = mock_repo

    with pytest.raises(RuntimeError):
        await saver.save_batch([{"doc_id": "ok"}, {"doc_id": "bad"}])
