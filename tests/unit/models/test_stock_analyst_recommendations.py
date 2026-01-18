from __future__ import annotations

from app.models import stock_analyst_recommendations


def test_stock_analyst_recommendations_model_basic():
    cls = stock_analyst_recommendations.StockAnalystRecommendations
    assert cls.__tablename__ == "stock_analyst_recommendations"
    ann = getattr(cls, "__annotations__", {})
    assert isinstance(ann, dict)
    assert "id" in ann or len(ann) >= 1
