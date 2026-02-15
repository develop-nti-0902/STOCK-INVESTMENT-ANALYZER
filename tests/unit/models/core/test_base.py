"""Tests for model base utilities and mixins."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.core import base


def test_camel_to_snake_basic_cases():
    """Verify CamelCase to snake_case conversion works as expected."""
    cases = {
        "MyModel": "my_model",
        "HTTPResponse": "http_response",
        "MyXMLParser": "my_xml_parser",
        "already_snake": "already_snake",
    }

    for class_name, expected in cases.items():
        cls = type(class_name, (base.SerialPKMixin, base.Base), {})
        assert cls.__tablename__ == expected


def test_tablename_auto_assigned_and_preserved():
    """テーブル名の自動割当と明示的指定が機能することを検証する."""

    class SampleModel(base.SerialPKMixin, base.Base):
        pass

    class CustomName(base.SerialPKMixin, base.Base):
        __tablename__ = "custom_table"

    assert SampleModel.__tablename__ == "sample_model"
    assert CustomName.__tablename__ == "custom_table"


def test_timestamp_mixin_sets_defaults_and_respects_kwargs():
    """TimestampMixin がデフォルト値を設定し、引数を尊重することを確認する."""

    class TimeModel(base.SerialPKMixin, base.TimestampMixin, base.Base):
        pass

    before = datetime.now(timezone.utc)
    inst = TimeModel()
    after = datetime.now(timezone.utc)

    assert hasattr(inst, "created_at")
    assert hasattr(inst, "updated_at")
    assert isinstance(inst.created_at, datetime)
    assert isinstance(inst.updated_at, datetime)

    lower = before - timedelta(seconds=1)
    upper = after + timedelta(seconds=1)
    assert lower <= inst.created_at <= upper
    assert lower <= inst.updated_at <= upper

    custom = datetime(2000, 1, 1, 0, 0, 0)
    inst2 = TimeModel(created_at=custom)
    assert inst2.created_at == custom

    inst3 = TimeModel(created_at=None)
    assert isinstance(inst3.created_at, datetime)
    assert inst3.created_at is not None


def test_timestamp_mixin_updated_at_on_init_is_recent():
    """初期化直後の `updated_at` が最近時刻であることを確認する."""

    class TimeModel2(base.SerialPKMixin, base.TimestampMixin, base.Base):
        pass

    inst = TimeModel2()
    now = datetime.now(timezone.utc)
    delta = now - inst.updated_at
    assert abs(delta.total_seconds()) < 2.0
