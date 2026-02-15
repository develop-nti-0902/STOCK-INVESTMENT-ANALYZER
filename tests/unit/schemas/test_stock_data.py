"""Unit tests for stock data schemas."""

from datetime import datetime, timezone

from app.schemas.stock_data import StockPriceCreate


def test_stock_price_symbol_validator():
    """StockPriceCreate の symbol 正規化を検証する."""
    obj = StockPriceCreate(
        symbol="  aapl  ",
        timestamp=datetime.now(timezone.utc),
    )
    assert obj.symbol == "AAPL"
