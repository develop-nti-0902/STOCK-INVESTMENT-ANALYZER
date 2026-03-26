"""`Nikkei225Validator` の単体テスト.

バイパス実装の振る舞い（常に成功を返す）を検証します。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.data_synchronization.market_data.nikkei225.validator import Nikkei225Validator


@pytest.fixture
def validator() -> Nikkei225Validator:
    """テスト対象インスタンスを返す."""
    return Nikkei225Validator()


# ---------------------------------------------------------------------------
# バイパス実装の検証
# ---------------------------------------------------------------------------


def test_validate_returns_valid_true(validator: Nikkei225Validator):
    """validate は常に is_valid=True を返すこと（バイパス実装）."""
    result = validator.validate([])
    assert result.is_valid is True


def test_validate_returns_no_errors(validator: Nikkei225Validator):
    """validate は errors が空であること."""
    result = validator.validate({"some": "data"})
    assert result.errors == []


def test_validate_returns_bypass_warning(validator: Nikkei225Validator):
    """validate は warnings に 'bypassed' を含むメッセージを返すこと."""
    result = validator.validate(None)
    assert any("bypassed" in w.lower() or "bypass" in w.lower() for w in result.warnings)


@pytest.mark.parametrize(
    "input_data",
    [
        None,
        [],
        {},
        "string",
        123,
        [{"timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc), "close": 27200.0}],
    ],
)
def test_validate_accepts_any_input_and_bypasses(validator: Nikkei225Validator, input_data):
    """どんな入力型に対してもバイパスして成功を返すこと."""
    result = validator.validate(input_data)
    assert result.is_valid is True
    assert result.errors == []
