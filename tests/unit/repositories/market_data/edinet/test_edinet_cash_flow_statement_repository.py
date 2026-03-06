"""Unit tests for EdinetCashFlowStatementRepository."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.edinet import EdinetCashFlowStatement
from app.repositories.market_data.edinet.edinet_cash_flow_statement_repository import (
    EdinetCashFlowStatementRepository,
)


def test_model_tablename_and_attrs():
    """モデルのテーブル名と属性が正しく定義されていることを検証する."""
    assert getattr(EdinetCashFlowStatement, "__tablename__") == "edinet_cash_flow_statement"
    for attr in (
        "doc_id",
        "sec_code",
        "submission_date",
        "period_end_date",
        "operating_cf",
    ):
        assert hasattr(EdinetCashFlowStatement, attr), f"Missing attribute: {attr}"


@pytest.mark.asyncio
async def test_repository_upsert_raises_on_empty_data():
    """空データ渡しで upsert が ValueError を送出することを検証する."""
    repo = EdinetCashFlowStatementRepository(session=object())
    with pytest.raises(ValueError):
        await repo.upsert({})


@pytest.mark.asyncio
async def test_find_latest_and_find_by_period_calls_execute(monkeypatch):
    """find_latest_by_sec_code と find_by_period が内部で execute を呼ぶことを検証する."""
    called = {}

    class DummyResult:
        def __init__(self, value=None):
            self._value = value

        def scalar_one_or_none(self):
            return self._value

        def scalars(self):
            class S:
                def __init__(self, items):
                    self._items = items

                def all(self):
                    return self._items

            return S(self._value or [])

    async def fake_execute(self, stmt):
        called["ok"] = True
        return DummyResult()

    repo = EdinetCashFlowStatementRepository(session=object())
    repo.session = type("S", (), {"execute": fake_execute})()

    res = await repo.find_latest_by_sec_code("7203")
    assert res is None
    res2 = await repo.find_by_period("7203", date(2024, 3, 31))
    assert res2 is None
    assert called.get("ok", False)


@pytest.mark.asyncio
async def test_save_batch_upsert_success():
    """save_batch_upsert がバッチ処理を実行し、モデルリストを返すことを確認する."""
    mock_session = MagicMock()
    mock_session.flush = AsyncMock()

    # Mock the result object with fetchall() for RETURNING clause
    mock_rows = [
        MagicMock(
            _mapping={
                "doc_id": "D1",
                "sec_code": "7203",
                "submission_date": date(2024, 4, 1),
                "period_end_date": date(2024, 3, 31),
                "fiscal_year": 2024,
                "operating_cf": 1000.0,
            }
        ),
        MagicMock(
            _mapping={
                "doc_id": "D2",
                "sec_code": "9984",
                "submission_date": date(2024, 4, 1),
                "period_end_date": date(2024, 3, 31),
                "fiscal_year": 2024,
                "operating_cf": 2000.0,
            }
        ),
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows

    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = EdinetCashFlowStatementRepository(mock_session)

    data_list = [
        {
            "doc_id": "D1",
            "sec_code": "7203",
            "submission_date": date(2024, 4, 1),
            "period_end_date": date(2024, 3, 31),
        },
        {
            "doc_id": "D2",
            "sec_code": "9984",
            "submission_date": date(2024, 4, 1),
            "period_end_date": date(2024, 3, 31),
        },
    ]

    res = await repo.save_batch(data_list)

    assert len(res) == 2
    assert res[0].sec_code == "7203"
    assert res[1].sec_code == "9984"
    mock_session.execute.assert_awaited()
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_save_batch_upsert_empty_list():
    """save_batch_upsert で空リストの場合、空リストを返すことを確認する."""
    mock_session = MagicMock()
    repo = EdinetCashFlowStatementRepository(mock_session)

    res = await repo.save_batch([])
    assert res == []


@pytest.mark.asyncio
async def test_save_batch_upsert_none_raises():
    """save_batch_upsert で None の場合に ValueError を発生させることを確認する."""
    mock_session = MagicMock()
    repo = EdinetCashFlowStatementRepository(mock_session)

    with pytest.raises(ValueError, match="data_list is required for save_batch_upsert"):
        await repo.save_batch(None)
