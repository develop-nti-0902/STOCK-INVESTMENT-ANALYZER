"""Unit tests for Edinet profit and loss model."""

from importlib import import_module

mod = import_module("app.models.market_data.edinet.edinet_profit_and_loss")


def test_edinet_profit_and_loss_exported():
    """edinet_profit_and_loss モジュールのエクスポート確認."""
    assert "EdinetProfitAndLoss" in getattr(mod, "__all__", [])
