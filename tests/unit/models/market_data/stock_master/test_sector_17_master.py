"""Tests for Sector17Master model."""

from app.models.market_data.stock_master import Sector17Master


def test_sector_17_master_creation():
    """Sector17Master の作成テスト."""
    master = Sector17Master(code="1", name="水産物・農産物")
    assert master.code == "1"
    assert master.name == "水産物・農産物"
