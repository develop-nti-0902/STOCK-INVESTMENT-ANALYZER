"""Tests for model base utilities and mixins."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.core import base


def test_camel_to_snake_basic_cases():
    """Verify CamelCase to snake_case conversion works as expected."""
    # Arrange: クラス名を通じて公開APIで変換動作を検証する
    cases = {
        "MyModel": "my_model",
        "HTTPResponse": "http_response",
        "MyXMLParser": "my_xml_parser",
        "already_snake": "already_snake",
    }

    # Act/Assert: 動的にクラスを作成して __tablename__ を確認する
    for class_name, expected in cases.items():
        # DeclarativeBase のサブクラスとして動的に定義することで
        # 内部のスネークケース変換処理を通す
        cls = type(class_name, (base.SerialPKMixin, base.Base), {})
        assert cls.__tablename__ == expected


def test_tablename_auto_assigned_and_preserved():
    """Verify `__tablename__` is auto-assigned and explicit names are preserved."""

    # Arrange: ダミーモデル定義（__tablename__ 未指定 / 指定）
    class SampleModel(base.SerialPKMixin, base.Base):
        pass

    class CustomName(base.SerialPKMixin, base.Base):
        __tablename__ = "custom_table"

    # Act & Assert: 自動付与と保持を確認
    assert SampleModel.__tablename__ == "sample_model"
    assert CustomName.__tablename__ == "custom_table"


def test_timestamp_mixin_sets_defaults_and_respects_kwargs():
    """Verify TimestampMixin sets defaults, respects kwargs, and handles None."""

    # Arrange: ダミーモデルを定義
    class TimeModel(base.SerialPKMixin, base.TimestampMixin, base.Base):
        pass

    # Act: 何も渡さずにインスタンス化
    before = datetime.now(timezone.utc)
    inst = TimeModel()
    after = datetime.now(timezone.utc)

    # Assert: created_at / updated_at が設定されていること
    assert hasattr(inst, "created_at")
    assert hasattr(inst, "updated_at")
    assert isinstance(inst.created_at, datetime)
    assert isinstance(inst.updated_at, datetime)

    # created_at は before と after の間であること
    lower = before - timedelta(seconds=1)
    upper = after + timedelta(seconds=1)
    assert lower <= inst.created_at <= upper
    assert lower <= inst.updated_at <= upper

    # Act: 明示的な値を渡す
    custom = datetime(2000, 1, 1, 0, 0, 0)
    inst2 = TimeModel(created_at=custom)
    # Assert: 提供した値が保持される
    assert inst2.created_at == custom

    # Act: None を渡す
    inst3 = TimeModel(created_at=None)
    # Assert: None が渡されても現在時刻で埋められる
    assert isinstance(inst3.created_at, datetime)
    assert inst3.created_at is not None


def test_timestamp_mixin_updated_at_on_init_is_recent():
    """Check that `updated_at` on init is recent."""

    # Arrange: ダミーモデル定義
    class TimeModel2(base.SerialPKMixin, base.TimestampMixin, base.Base):
        pass

    # Act: インスタンス生成
    inst = TimeModel2()
    now = datetime.now(timezone.utc)

    # Assert: 更新時刻が最近であること
    delta = now - inst.updated_at
    assert abs(delta.total_seconds()) < 2.0
