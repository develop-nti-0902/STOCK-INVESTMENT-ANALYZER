from __future__ import annotations

from app.models import stock_balance_sheet_annual


def test_stock_balance_sheet_annual_model_basic():
    cls = stock_balance_sheet_annual.StockBalanceSheetAnnual
    assert cls.__tablename__ == "stock_balance_sheet_annual"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
