"""Tests for the EdinetDividendMetrics SQLAlchemy model."""

from app.models.market_data.edinet import EdinetDividendMetrics


def test_model_has_tablename():
    """モデルが正しいテーブル名を持つことを確認する。"""
    assert hasattr(EdinetDividendMetrics, "__tablename__")
    assert EdinetDividendMetrics.__tablename__ == "edinet_dividend_metrics"
