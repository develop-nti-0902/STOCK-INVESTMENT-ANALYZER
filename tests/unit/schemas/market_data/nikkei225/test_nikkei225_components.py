"""Nikkei225Component スキーマのユニットテスト."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.schemas.market_data.nikkei225 import Nikkei225ComponentCreate


def test_nikkei225_component_create_schema() -> None:
    """スキーマ検証が正しく動作すること."""
    schema = Nikkei225ComponentCreate(
        stock_code="7203",
        price_adjustment_factor=Decimal("50.0"),
        effective_date=date(2026, 4, 18),
    )
    assert schema.stock_code == "7203"
