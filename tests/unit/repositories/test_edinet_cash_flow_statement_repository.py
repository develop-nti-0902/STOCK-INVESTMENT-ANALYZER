"""Unit tests for EdinetCashFlowStatementRepository."""

from __future__ import annotations

from datetime import date

import pytest

from app.models.edinet_cash_flow_statement import EdinetCashFlowStatement
from app.repositories.edinet_cash_flow_statement_repository import EdinetCashFlowStatementRepository


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
