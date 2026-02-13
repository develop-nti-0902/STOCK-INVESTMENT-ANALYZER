"""Tests for EdinetCashFlowStatementConverter."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.market_data.edinet.edinet_cash_flow_statement.converter import (
    EdinetCashFlowStatementConverter,
)


def test_to_pydantic_and_from_pydantic():
    """Pydantic 変換と逆変換が期待どおりに動作することを検証する."""
    conv = EdinetCashFlowStatementConverter()

    data = {
        "doc_id": "S100N8ST",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end": date(2024, 3, 31),
        "period_end_date": date(2024, 3, 31),
        "operating_cf": 1234.56,
        "report_type": "annual",
    }

    model = conv.to_pydantic(data)
    assert model.doc_id == "S100N8ST"
    assert model.sec_code == "7203"
    assert isinstance(model.operating_cf, Decimal)
    assert model.operating_cf == Decimal("1234.56")

    rec = conv.from_pydantic(model)
    assert rec["operating_cf"] == model.operating_cf


def test_to_pydantic_missing_period_end_raises():
    """period_end が欠けた場合に例外が発生することを検証する."""
    conv = EdinetCashFlowStatementConverter()
    bad = {"doc_id": "S1", "sec_code": "7203"}
    with pytest.raises(ValueError):
        conv.to_pydantic(bad)
