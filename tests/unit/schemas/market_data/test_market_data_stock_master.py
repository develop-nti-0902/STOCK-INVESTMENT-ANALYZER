"""
market_data の銘柄マスタスキーマの単体テスト
"""

from pydantic import ValidationError

from app.schemas.market_data.stock_master import (
    StockMasterNormalized,
    StockMasterRaw,
    StockMasterResponse,
)


def test_stock_master_raw_aliases_and_values():
    raw = StockMasterRaw(
        **{"日付": "20250101", "コード": 1234, "銘柄名": "TestCo"}
    )
    assert raw.date == "20250101"
    assert raw.code == 1234
    assert raw.name == "TestCo"


def test_stock_master_normalized_requires_mandatory_fields():
    # missing required fields should raise
    try:
        StockMasterNormalized()
        assert False, "Expected ValidationError"
    except ValidationError:
        pass

    nm = StockMasterNormalized(stock_code="7203", stock_name="Toyota")
    assert nm.stock_code == "7203"
    assert nm.stock_name == "Toyota"


def test_stock_master_response_includes_id():
    r = StockMasterResponse(stock_code="7203", stock_name="Toyota", id=5)
    assert r.id == 5
    assert r.stock_code == "7203"
