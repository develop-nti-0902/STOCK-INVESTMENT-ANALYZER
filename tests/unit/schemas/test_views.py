"""Unit tests for schema views exports."""

from app.schemas import views as mod


def test_views_exports():
    """views モジュールが期待するエクスポートを持つことを確認する."""
    assert "LatestStockResponse" in getattr(mod, "__all__", [])
