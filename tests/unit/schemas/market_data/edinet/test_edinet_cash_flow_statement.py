"""Unit tests for EdinetCashFlowStatement schemas."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.schemas.market_data.edinet import EdinetCashFlowStatementCreate


def test_create_schema_decimal_and_strip():
    """正しい数値文字列が Decimal に変換され、文字列トリムが行われることを検証する."""
    payload = {
        "doc_id": " S100N8ST ",
        "sec_code": " 7203 ",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "report_type": "annual",
        "operating_cf": "1234.56",
    }

    schema = EdinetCashFlowStatementCreate(**payload)
    assert schema.doc_id == "S100N8ST"
    assert schema.sec_code == "7203"
    assert isinstance(schema.operating_cf, Decimal)
    assert schema.operating_cf == Decimal("1234.56")


def test_invalid_numeric_raises():
    """数値変換できない値でスキーマ生成が失敗することを検証する."""
    payload = {
        "doc_id": "S1",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "report_type": "annual",
        "operating_cf": "not-a-number",
    }

    with pytest.raises(ValueError):
        EdinetCashFlowStatementCreate(**payload)
