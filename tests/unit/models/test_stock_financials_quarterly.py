from __future__ import annotations

from app.models import stock_financials_quarterly


def test_stock_financials_quarterly_model_basic():
    cls = stock_financials_quarterly.StockFinancialsQuarterly
    assert cls.__tablename__ == "stock_financials_quarterly"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
