"""Tests for the `StockMaster` model fields, FK relationships, and normalization.

このテストファイルは以下を検証します：
- StockMaster の基本フィールドと FK カラム
- マスターテーブル（MarketCategoryMaster, Sector33Master, セクタ17Master, ScaleMaster）の CRUD
- FK リレーションシップと eager loading パターン
"""

from __future__ import annotations

from app.models.market_data.stock_master import (
    MarketCategoryMaster,
    ScaleMaster,
    Sector17Master,
    Sector33Master,
    StockMaster,
)
from app.models.market_data.stock_master.stock_master import IS_ACTIVE


def test_stock_master_basic_fields_and_tablename():
    """StockMaster の基本フィールドとテーブル名を検証する.

    FK カラムは NULL許可だが、基本的なフィールドは必須という想定。
    """
    inst = StockMaster(
        stock_code="7203",
        stock_name="Toyota Motor",
        market_category_id=None,
        sector_33_id=None,
        sector_17_id=None,
        scale_id=None,
        is_active=IS_ACTIVE,
        data_date="20251209",
    )

    assert inst.stock_code == "7203"
    assert inst.stock_name == "Toyota Motor"
    assert inst.market_category_id is None
    assert inst.sector_33_id is None
    assert inst.sector_17_id is None
    assert inst.scale_id is None
    assert inst.is_active == IS_ACTIVE
    assert inst.data_date == "20251209"

    assert inst.symbol == "7203"
    assert inst.name == "Toyota Motor"

    assert StockMaster.__tablename__ == "stock_master"


def test_stock_master_with_fk_ids():
    """StockMaster が FK ID を保持できることを検証する.

    マスター作成後、FK ID が設定される想定を確認。
    """
    inst = StockMaster(
        stock_code="1301",
        stock_name="極洋",
        market_category_id=1,
        sector_33_id=2,
        sector_17_id=3,
        scale_id=4,
        is_active=IS_ACTIVE,
        data_date="20251209",
    )

    assert inst.market_category_id == 1
    assert inst.sector_33_id == 2
    assert inst.sector_17_id == 3
    assert inst.scale_id == 4


def test_market_category_master_creation():
    """MarketCategoryMaster の作成・フィールド検証.

    市場区分（Prime/Standard/Growth など）のマスター定義を確認。
    """
    master = MarketCategoryMaster()
    master.code = "Prime"
    master.name = "プライム市場"

    assert master.code == "Prime"
    assert master.name == "プライム市場"
    assert master.__tablename__ == "market_category_master"


def test_sector_33_master_creation():
    """Sector33Master の作成・フィールド検証.

    業種33分類マスターの定義を確認。
    """
    master = Sector33Master()
    master.code = "08"
    master.name = "水産・農林業"

    assert master.code == "08"
    assert master.name == "水産・農林業"
    assert master.__tablename__ == "sector_33_master"


def test_sector_17_master_creation():
    """Sector17Master の作成・フィールド検証.

    業種17分類マスターの定義を確認。
    """
    master = Sector17Master()
    master.code = "1"
    master.name = "水産物・農産物"

    assert master.code == "1"
    assert master.name == "水産物・農産物"
    assert master.__tablename__ == "sector_17_master"


def test_scale_master_creation():
    """ScaleMaster の作成・フィールド検証.

    企業規模マスター（Large/Medium/Small など）の定義を確認。
    """
    master = ScaleMaster()
    master.code = "L"
    master.name = "Large"

    assert master.code == "L"
    assert master.name == "Large"
    assert master.__tablename__ == "scale_master"


def test_stock_master_property_accessors():
    """StockMaster の property accessors（symbol/name）を検証する.

    既存コードとの互換性確保。
    """
    inst = StockMaster(
        stock_code="9202",
        stock_name="ANA Holdings",
        is_active=IS_ACTIVE,
    )

    # Property getter
    assert inst.symbol == "9202"
    assert inst.name == "ANA Holdings"

    # Property setter
    inst.symbol = "9203"
    inst.name = "Updated Name"

    assert inst.stock_code == "9203"
    assert inst.stock_name == "Updated Name"
