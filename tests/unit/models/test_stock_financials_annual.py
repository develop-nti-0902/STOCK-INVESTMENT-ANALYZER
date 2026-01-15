from __future__ import annotations

from app.models import stock_financials_annual


def test_stock_financials_annual_model_basic():
    cls = stock_financials_annual.StockFinancialsAnnual
    assert cls.__tablename__ == "stock_financials_annual"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
