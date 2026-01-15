from __future__ import annotations

from app.models import stock_holders_mutualfund


def test_stock_holders_mutualfund_model_basic():
    cls = stock_holders_mutualfund.StockHoldersMutualfund
    assert cls.__tablename__ == "stock_holders_mutualfund"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
