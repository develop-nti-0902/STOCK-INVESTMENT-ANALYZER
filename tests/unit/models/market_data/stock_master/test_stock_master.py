"""Tests for the `StockMaster` model fields and table naming."""

from __future__ import annotations

from app.models.market_data import stock_master


def test_stock_master_basic_fields_and_tablename():
    """StockMaster の基本フィールドとテーブル名を検証する."""
    inst = stock_master.StockMaster(
        stock_code="7203",
        stock_name="Toyota Motor",
        market_category="TSE",
        sector_code_33="01",
        sector_name_33="Automobile",
        is_active=stock_master.IS_ACTIVE,
        data_date="19490516",
    )

    assert inst.stock_code == "7203"
    assert inst.stock_name == "Toyota Motor"
    assert inst.market_category == "TSE"
    assert inst.sector_name_33 == "Automobile"
    assert inst.is_active == stock_master.IS_ACTIVE
    assert inst.data_date == "19490516"

    assert inst.symbol == "7203"
    assert inst.name == "Toyota Motor"

    assert stock_master.StockMaster.__tablename__ == "stock_master"
