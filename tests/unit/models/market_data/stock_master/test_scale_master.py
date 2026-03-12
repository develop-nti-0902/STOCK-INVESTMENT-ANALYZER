"""Tests for ScaleMaster model."""

from app.models.market_data.stock_master import ScaleMaster


def test_scale_master_creation():
    """ScaleMaster の作成テスト."""
    master = ScaleMaster(code="L", name="Large")
    assert master.code == "L"
    assert master.name == "Large"
