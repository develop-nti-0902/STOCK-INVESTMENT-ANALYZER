from __future__ import annotations

from app.models import stock_holders_institutional


def test_stock_holders_institutional_model_basic():
    cls = stock_holders_institutional.StockHoldersInstitutional
    assert cls.__tablename__ == "stock_holders_institutional"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
