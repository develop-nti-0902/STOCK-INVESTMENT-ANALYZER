"""Unit tests for market_data stock price schema."""

from datetime import datetime, timezone

from app.schemas.market_data.stock_price import StockData


def test_stock_data_basic_fields():
    """Verify StockData basic fields and types."""
    dt = datetime.now(timezone.utc)
    s = StockData(symbol="AAPL", timestamp=dt, open_price=100.0, close=101.0)
    assert s.symbol == "AAPL"
    assert s.timestamp == dt
    assert s.open_price == 100.0
    assert s.close == 101.0
