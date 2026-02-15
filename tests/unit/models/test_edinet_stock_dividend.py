"""Unit tests for app.models.edinet_stock_dividend."""

from __future__ import annotations

from datetime import date

from app.models.edinet_stock_dividend import EdinetStockDividend


def test_model_repr_contains_key_fields():
    """モデルのreprが主要フィールドを含むことを検証する."""
    m = EdinetStockDividend(
        doc_id="D1",
        sec_code="7203",
        submission_date=date(2024, 4, 1),
        period_end_date=date(2024, 3, 31),
        fiscal_year=2024,
        report_type="annual",
        dividend_actual=12.34,
    )

    r = repr(m)
    assert "7203" in r
    assert "datetime.date(2024, 3, 31)" in r
