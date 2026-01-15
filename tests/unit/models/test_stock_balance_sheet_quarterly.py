from __future__ import annotations

from app.models import stock_balance_sheet_quarterly


def test_stock_balance_sheet_quarterly_model_basic():
    cls = stock_balance_sheet_quarterly.StockBalanceSheetQuarterly
    assert cls.__tablename__ == "stock_balance_sheet_quarterly"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
