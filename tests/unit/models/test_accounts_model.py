"""Tests for the `accounts` model."""

from __future__ import annotations

from app.models import accounts


def test_account_fields_and_repr():
    """Verify account model fields and representation."""
    # マッピングでのカラムデフォルトはインスタンス作成時に必ず設定されないため
    # 確認したい値は明示して渡す
    inst = accounts.Account(
        email="user@example.com",
        hashed_password="pwd",
        is_active=True,
        is_superuser=False,
    )

    assert inst.email == "user@example.com"
    assert inst.hashed_password == "pwd"
    assert inst.full_name is None
    assert inst.is_active is True
    assert inst.is_superuser is False
    assert inst.provider is None
    assert inst.external_id is None

    r = repr(inst)
    assert "user@example.com" in r
