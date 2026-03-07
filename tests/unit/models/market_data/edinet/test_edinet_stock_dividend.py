"""Unit tests for app.models.edinet_stock_dividend."""

from __future__ import annotations

from datetime import date

from app.models.market_data.edinet import EdinetStockDividend


def test_model_repr_contains_key_fields():
    """モデルのreprが主要フィールドを含むことを検証する."""
    m = EdinetStockDividend(
        edinet_document_id=1,
        period_end_date=date(2024, 3, 31),
        fiscal_year=2024,
        dividend_actual=12.34,
    )

    r = repr(m)
    assert "datetime.date(2024, 3, 31)" in r
    assert "period_end_date" in r
