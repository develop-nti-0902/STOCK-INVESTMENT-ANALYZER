from __future__ import annotations

from app.models import stock_financial_info


def test_stock_financial_info_model_basic():
    cls = stock_financial_info.StockFinancialInfo
    assert cls.__tablename__ == "stock_financial_info"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
