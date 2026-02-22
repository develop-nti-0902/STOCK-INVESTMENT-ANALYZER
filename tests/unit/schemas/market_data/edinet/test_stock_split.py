"""Tests for StockSplit schemas."""

from __future__ import annotations

from datetime import date

from app.schemas.market_data.edinet.stock_split import StockSplitCreate


def test_stock_split_schema_accepts_and_converts_ratios() -> None:
    """Test that schema accepts and converts ratios."""
    payload = {
        "code": "  37980 ",
        "effective_date": date(2023, 10, 1),
        "ratio_from": "1",
        "ratio_to": "2",
    }

    schema = StockSplitCreate(**payload)
    assert schema.code == "37980"
    assert schema.ratio_from == 1
    assert schema.ratio_to == 2
