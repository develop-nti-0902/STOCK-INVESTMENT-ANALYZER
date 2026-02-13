"""`StockMasterConverter` の単体テスト.

テスト方針:
 - `StockMasterNormalized` インスタンスのリストを `to_records` に渡し、
     各モデルが辞書に変換され、`None` の値が除外されていることを検証します.
"""

from typing import List

from app.schemas.market_data.stock_master import StockMasterNormalized
from app.services.market_data.stock_master.converter import StockMasterConverter


def test_to_records_converts_models_to_dicts():
    """モデルリストが辞書リストに変換されることを確認する."""
    models: List[StockMasterNormalized] = [
        StockMasterNormalized(
            stock_code="1234",
            stock_name="Test Co",
            market_category="1部",
            data_date="20240101",
            is_active=1,
        ),
        StockMasterNormalized(
            stock_code="5678",
            stock_name="Another Co",
            market_category=None,
            data_date=None,
            is_active=0,
        ),
    ]

    conv = StockMasterConverter()
    records = conv.to_records(models)

    assert isinstance(records, list)
    assert len(records) == 2
    # 各要素は dict で、必須フィールドが存在する
    assert records[0]["stock_code"] == "1234"
    assert records[0]["stock_name"] == "Test Co"
    assert records[0]["data_date"] == "20240101"
    assert records[1]["stock_code"] == "5678"
    assert records[1]["stock_name"] == "Another Co"


def test_to_records_excludes_none_values():
    """`exclude_none=True` によって None 値が除外されることを確認する."""
    model = StockMasterNormalized(
        stock_code="9999",
        stock_name="Optional Co",
        market_category=None,
        sector_code_33=None,
        data_date=None,
        is_active=1,
    )

    conv = StockMasterConverter()
    records = conv.to_records([model])

    assert len(records) == 1
    rec = records[0]
    # None のフィールドは出力辞書に含まれない
    assert "market_category" not in rec
    assert "sector_code_33" not in rec
    assert "data_date" not in rec
    # 必須フィールドは含まれる
    assert rec["stock_code"] == "9999"
    assert rec["stock_name"] == "Optional Co"
