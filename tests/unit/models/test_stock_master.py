"""Tests for the `StockMaster` model fields and table naming."""

from __future__ import annotations

from app.models import stock_master


def test_stock_master_basic_fields_and_tablename():
    """Verify StockMaster fields match DB schema and tablename assignment."""
    # Arrange / Act: インスタンス化（DB側カラム名で指定）
    inst = stock_master.StockMaster(
        stock_code="7203",
        stock_name="Toyota Motor",
        market_category="TSE",
        sector_code_33="01",
        sector_name_33="Automobile",
        is_active=stock_master.IS_ACTIVE,
        data_date="19490516",
    )

    # Assert: 属性が正しくセットされている
    assert inst.stock_code == "7203"
    assert inst.stock_name == "Toyota Motor"
    assert inst.market_category == "TSE"
    assert inst.sector_name_33 == "Automobile"
    assert inst.is_active == stock_master.IS_ACTIVE
    assert inst.data_date == "19490516"

    # 互換性プロパティも確認（symbol/name）
    assert inst.symbol == "7203"
    assert inst.name == "Toyota Motor"

    # テーブル名の自動付与を確認
    assert stock_master.StockMaster.__tablename__ == "stock_master"
