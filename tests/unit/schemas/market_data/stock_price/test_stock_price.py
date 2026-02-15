"""market_data の株価スキーマ単体テスト (互換コピー)."""

from datetime import datetime, timezone

from app.schemas.market_data.stock_price import StockData


def test_stock_data_basic_fields():
    """StockData の基本フィールドが正しく設定されることを検証する."""
    dt = datetime.now(timezone.utc)
    s = StockData(symbol="AAPL", timestamp=dt, open_price=100.0, close=101.0)
    assert s.symbol == "AAPL"
    assert s.timestamp == dt
    assert s.open_price == 100.0
    assert s.close == 101.0
