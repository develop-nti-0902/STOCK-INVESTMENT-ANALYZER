"""Nikkei225Component モデルのユニットテスト."""

from __future__ import annotations

from app.models.market_data.nikkei225 import Nikkei225Component


def test_nikkei225_component_table_name() -> None:
    """テーブル名が正しいこと."""
    assert Nikkei225Component.__tablename__ == "nikkei225_components"
