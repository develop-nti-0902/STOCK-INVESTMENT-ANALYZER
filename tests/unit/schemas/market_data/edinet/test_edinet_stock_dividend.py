"""Unit tests for app.schemas.edinet_stock_dividend."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.schemas.market_data.edinet import EdinetStockDividendCreate, EdinetStockDividendLatest


def test_schema_converts_and_strips():
    """入力のトリムと型変換が正しく行われることを検証する."""
    payload = {
        "doc_id": " DOC123 ",
        "sec_code": " 7203 ",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "fiscal_year": 2024,
        "report_type": "annual",
        "dividend_actual": "12.34",
    }

    s = EdinetStockDividendCreate(**payload)
    assert s.doc_id == "DOC123"
    assert s.sec_code == "7203"
    assert isinstance(s.dividend_actual, Decimal)
    assert s.dividend_actual == Decimal("12.34")


def test_schema_invalid_dividend_raises():
    """無効な配当値でスキーマが例外を投げることを確認する."""
    payload = {
        "doc_id": "D1",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "fiscal_year": 2024,
        "report_type": "annual",
        "dividend_actual": "not-a-number",
    }

    with pytest.raises(ValueError):
        EdinetStockDividendCreate(**payload)


def test_latest_schema_fields():
    """最新スキーマのフィールドが期待通りであることを検証する."""
    latest = EdinetStockDividendLatest(
        sec_code="7203", period_end_date=date(2024, 3, 31), dividend_actual=Decimal("1.23")
    )
    assert latest.sec_code == "7203"
    assert latest.dividend_actual == Decimal("1.23")
