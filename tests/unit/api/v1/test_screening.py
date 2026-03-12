"""tests for `app.api.v1.screening`.

簡易的に `router` が公開されていることを確認する。
"""

from fastapi import APIRouter

from app.api.v1 import screening as screening_module


def test_screening_router_exists():
    """`screening` モジュールが `router` を公開していることを確認する簡易テスト。"""
    assert hasattr(screening_module, "router")
    assert isinstance(screening_module.router, APIRouter)
