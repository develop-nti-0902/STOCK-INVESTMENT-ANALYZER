from __future__ import annotations

from app.models import stock_cashflow_quarterly


def test_stock_cashflow_quarterly_model_basic():
    cls = stock_cashflow_quarterly.StockCashflowQuarterly
    assert cls.__tablename__ == "stock_cashflow_quarterly"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
