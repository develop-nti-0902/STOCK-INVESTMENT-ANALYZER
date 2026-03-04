"""Tests for Sector33Master model."""

from app.models.market_data.stock_master import Sector33Master


def test_sector_33_master_creation():
    """Sector33Master の作成テスト."""
    master = Sector33Master(code="08", name="水産・農林業")
    assert master.code == "08"
    assert master.name == "水産・農林業"
