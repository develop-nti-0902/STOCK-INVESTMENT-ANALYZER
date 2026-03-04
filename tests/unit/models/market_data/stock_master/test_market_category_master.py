"""Tests for MarketCategoryMaster model."""

from app.models.market_data.stock_master import MarketCategoryMaster


def test_market_category_master_creation():
    """MarketCategoryMaster の作成テスト."""
    master = MarketCategoryMaster(code="Prime", name="プライム市場")
    assert master.code == "Prime"
    assert master.name == "プライム市場"
