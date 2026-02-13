"""Unit tests for EdinetStockDividendConverter."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.schemas.edinet_stock_dividend import EdinetStockDividendCreate
from app.services.market_data.edinet.stock_dividend.converter import EdinetStockDividendConverter


def test_to_pydantic_success():
    """辞書データから Pydantic モデルへの変換が成功することを検証する."""
    data = {
        "doc_id": "DUMMY",
        "sec_code": "7203",
        "submission_date": "2025-02-01",
        "period_end_date": "2024-03-31",
        "dividend_actual": "12.5",
    }

    conv = EdinetStockDividendConverter()
    model = conv.to_pydantic(data)

    assert isinstance(model, EdinetStockDividendCreate)
    assert model.fiscal_year == 2024
    assert isinstance(model.dividend_actual, Decimal)


def test_to_pydantic_missing_period_end_date_raises():
    """period_end_date が欠けている場合に例外が発生することを確認する."""
    data = {"doc_id": "D1", "sec_code": "X", "submission_date": "2025-01-01"}
    conv = EdinetStockDividendConverter()
    with pytest.raises(ValueError):
        conv.to_pydantic(data)


def test_decimal_conversion_invalid_values_produce_none():
    """無効な数値文字列は None に変換されることを確認する."""
    data = {
        "doc_id": "D2",
        "sec_code": "0001",
        "submission_date": "2025-01-01",
        "period_end_date": "2024-12-31",
        "dividend_actual": "not_a_number",
    }
    conv = EdinetStockDividendConverter()
    model = conv.to_pydantic(data)

    assert model.dividend_actual is None


def test_from_dataframe_not_implemented():
    """from_dataframe が未実装で NotImplementedError を出すことを検証する."""
    conv = EdinetStockDividendConverter()
    with pytest.raises(NotImplementedError):
        conv.from_dataframe(None)
