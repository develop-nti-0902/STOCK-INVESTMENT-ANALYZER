from __future__ import annotations

from app.models import stock_splits


def test_stock_splits_model_basic():
    cls = stock_splits.StockSplits
    assert cls.__tablename__ == "stock_splits"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
