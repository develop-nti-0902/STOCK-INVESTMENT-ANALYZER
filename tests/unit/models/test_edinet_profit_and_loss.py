"""Unit tests for Edinet profit and loss model."""

from app.models import edinet_profit_and_loss as mod


def test_edinet_profit_and_loss_exported():
    """edinet_profit_and_loss モジュールのエクスポート確認."""
    assert "EdinetProfitAndLoss" in getattr(mod, "__all__", [])
