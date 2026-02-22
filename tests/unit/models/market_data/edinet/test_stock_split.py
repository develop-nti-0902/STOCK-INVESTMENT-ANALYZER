"""Tests for StockSplit model."""

from app.models.market_data.edinet.stock_split import StockSplit


def test_stock_split_model_has_expected_columns() -> None:
    """Test that StockSplit model contains expected columns."""
    split_cols = {c.name for c in StockSplit.__table__.columns}
    assert {"code", "effective_date", "ratio_from", "ratio_to"}.issubset(split_cols)
