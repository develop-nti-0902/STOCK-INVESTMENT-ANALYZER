"""Nikkei2251d モデル単体テスト."""

from __future__ import annotations

from sqlalchemy import UniqueConstraint

from app.models.market_data.nikkei225 import Nikkei2251d

EXPECTED_COLUMNS = {
    "id",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "created_at",
    "updated_at",
}


def test_table_name():
    """テーブル名が `nikkei225_1d` であること."""
    assert Nikkei2251d.__tablename__ == "nikkei225_1d"


def test_unique_constraint_exists():
    """`uix_nikkei225_1d_timestamp` ユニーク制約が定義されていること."""
    uix_names = [c.name for c in Nikkei2251d.__table_args__ if isinstance(c, UniqueConstraint)]
    assert "uix_nikkei225_1d_timestamp" in uix_names


def test_columns_match_expected():
    """カラム一覧が期待通りであること."""
    cols = {c.name for c in Nikkei2251d.__table__.columns}
    assert cols == EXPECTED_COLUMNS


def test_timestamp_column_not_nullable():
    """`timestamp` カラムが nullable=False であること."""
    col = Nikkei2251d.__table__.c["timestamp"]
    assert not col.nullable


def test_adj_close_column_nullable():
    """`adj_close` カラムが nullable=True であること."""
    col = Nikkei2251d.__table__.c["adj_close"]
    assert col.nullable


def test_volume_column_default_zero():
    """`volume` カラムのデフォルト値が 0 であること."""
    col = Nikkei2251d.__table__.c["volume"]
    assert col.default.arg == 0
