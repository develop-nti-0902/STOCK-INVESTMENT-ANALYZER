from __future__ import annotations

from app.models import stock_basic_info


def test_stock_basic_info_fields_and_repr():
    inst = stock_basic_info.StockBasicInfo(
        symbol="7203.T", short_name="Toyota"
    )

    assert inst.symbol == "7203.T"
    assert inst.short_name == "Toyota"
    assert inst.long_name is None
    assert inst.sector is None

    r = repr(inst)
    assert "7203.T" in r
