"""Unit tests for Edinet profit and loss schemas."""

from app.schemas import edinet_profit_and_loss as mod


def test_edinet_profit_and_loss_schema_exported():
    """edinet_profit_and_loss スキーマのエクスポート確認."""
    assert "EdinetProfitAndLossBase" in getattr(mod, "__all__", [])
