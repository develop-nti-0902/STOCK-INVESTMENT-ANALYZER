from __future__ import annotations

from app.models import stock_insider_transactions


def test_stock_insider_transactions_model_basic():
    cls = stock_insider_transactions.StockInsiderTransactions
    assert cls.__tablename__ == "stock_insider_transactions"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
