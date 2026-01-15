from __future__ import annotations

from app.models import stock_shares_outstanding


def test_stock_shares_outstanding_model_basic():
    cls = stock_shares_outstanding.StockSharesOutstanding
    assert cls.__tablename__ == "stock_shares_outstanding"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
