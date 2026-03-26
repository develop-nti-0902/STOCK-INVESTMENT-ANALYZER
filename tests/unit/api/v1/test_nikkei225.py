"""Unit tests for `app.api.v1.nikkei225` endpoints."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.v1 import nikkei225 as api_mod


class DummyService:
    """モックサービス実装（テスト用）."""

    def __init__(self, result=None):
        """初期化."""
        self._result = result or SimpleNamespace(
            success=True,
            records_fetched=10,
            records_saved=10,
            errors=[],
            elapsed_time=1.0,
        )

    async def fetch_and_save(self, *, max_period=None):
        """fetch_and_save のモック実装."""
        return self._result


# ── FetchRequest バリデーション ─────────────────────────────────────────────


def test_fetch_request_max_period_valid():
    """正の整数は受け付けること."""
    req = api_mod.FetchRequest(max_period=30)
    assert req.max_period == 30


def test_fetch_request_max_period_none():
    """省略時は None になること."""
    req = api_mod.FetchRequest()
    assert req.max_period is None


def test_fetch_request_max_period_zero_raises():
    """0 は gt=0 違反で ValidationError になること."""
    with pytest.raises(ValidationError):
        api_mod.FetchRequest(max_period=0)


def test_fetch_request_max_period_negative_raises():
    """負の値は gt=0 違反で ValidationError になること."""
    with pytest.raises(ValidationError):
        api_mod.FetchRequest(max_period=-1)


# ── FetchResponse 初期化 ───────────────────────────────────────────────────


def test_fetch_response_init():
    """FetchResponse が正常に初期化できること."""
    resp = api_mod.FetchResponse(
        success=True,
        records_fetched=5,
        records_saved=5,
        errors=[],
        elapsed_time=0.5,
    )
    assert resp.success is True
    assert resp.records_fetched == 5
    assert resp.records_saved == 5
    assert resp.errors == []
    assert resp.elapsed_time == 0.5


def test_fetch_response_errors_default_empty():
    """errors フィールドのデフォルトは空リストであること."""
    resp = api_mod.FetchResponse(
        success=False,
        records_fetched=0,
        records_saved=0,
        elapsed_time=0.1,
    )
    assert resp.errors == []


# ── ルーター確認 ──────────────────────────────────────────────────────────


def test_router_has_fetch_route():
    """`/fetch` エンドポイントが登録されていること."""
    paths = [r.path for r in api_mod.router.routes]
    assert "/fetch" in paths


# ── エンドポイント実行 ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_nikkei225_success():
    """モックサービスで成功レスポンスが返ること."""
    svc = DummyService()
    req = api_mod.FetchRequest(max_period=10)
    resp = await api_mod.fetch_nikkei225(req=req, service=svc)

    assert resp.success is True
    assert resp.records_fetched == 10
    assert resp.records_saved == 10
    assert resp.errors == []


@pytest.mark.asyncio
async def test_fetch_nikkei225_propagates_exception():
    """サービス例外は ServiceError として再送出されること."""
    from app.exceptions.business import ServiceError

    class BrokenService:
        async def fetch_and_save(self, *, max_period=None):
            raise RuntimeError("unexpected DB error")

    req = api_mod.FetchRequest()
    with pytest.raises(ServiceError):
        await api_mod.fetch_nikkei225(req=req, service=BrokenService())
