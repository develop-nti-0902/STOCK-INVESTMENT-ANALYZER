"""Nikkei225 日足スキーマ単体テスト."""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.market_data.nikkei225 import Nikkei2251dCreate, Nikkei2251dRead

_DT = datetime(2024, 1, 5, 0, 0, 0, tzinfo=timezone.utc)


# ── Nikkei2251dCreate ─────────────────────────────────────────────────────


def test_create_basic_fields():
    """`Nikkei2251dCreate` が基本フィールドで正常に作成できること."""
    obj = Nikkei2251dCreate(
        timestamp=_DT,
        open=35000.0,
        high=35100.0,
        low=34900.0,
        close=35050.0,
    )
    assert obj.timestamp == _DT
    assert obj.open == 35000.0
    assert obj.high == 35100.0
    assert obj.low == 34900.0
    assert obj.close == 35050.0
    assert obj.adj_close is None
    assert obj.volume == 0


def test_create_with_all_fields():
    """`adj_close` と `volume` を指定して正常に作成できること."""
    obj = Nikkei2251dCreate(
        timestamp=_DT,
        open=35000.0,
        high=35100.0,
        low=34900.0,
        close=35050.0,
        adj_close=35000.5,
        volume=500_000,
    )
    assert obj.adj_close == 35000.5
    assert obj.volume == 500_000


def test_create_adj_close_none_allowed():
    """`adj_close=None` が許容されること."""
    obj = Nikkei2251dCreate(
        timestamp=_DT,
        open=1.0,
        high=2.0,
        low=0.5,
        close=1.5,
        adj_close=None,
    )
    assert obj.adj_close is None


# ── Nikkei2251dRead ───────────────────────────────────────────────────────


def test_read_has_id_and_timestamps():
    """`Nikkei2251dRead` が id/created_at/updated_at を持つこと."""
    obj = Nikkei2251dRead(
        id=42,
        timestamp=_DT,
        open=35000.0,
        high=35100.0,
        low=34900.0,
        close=35050.0,
        created_at=_DT,
        updated_at=_DT,
    )
    assert obj.id == 42
    assert obj.created_at == _DT
    assert obj.updated_at == _DT


def test_read_inherits_create_fields():
    """`Nikkei2251dRead` が `Nikkei2251dCreate` のフィールドを継承すること."""
    obj = Nikkei2251dRead(
        id=1,
        timestamp=_DT,
        open=35000.0,
        high=35100.0,
        low=34900.0,
        close=35050.0,
        adj_close=34999.0,
        volume=100_000,
        created_at=_DT,
        updated_at=_DT,
    )
    assert obj.open == 35000.0
    assert obj.adj_close == 34999.0
    assert obj.volume == 100_000
