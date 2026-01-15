from __future__ import annotations

from app.models import stock_dividends


def test_stock_dividends_model_basic():
    cls = stock_dividends.StockDividends
    assert cls.__tablename__ == "stock_dividends"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
