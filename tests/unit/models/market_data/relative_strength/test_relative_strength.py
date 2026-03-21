"""Unit tests for `app.models.market_data.relative_strength.relative_strength` model."""

from datetime import date
from decimal import Decimal

from app.models.market_data.relative_strength import RelativeStrength


def test_relative_strength_model_creation():
    """RelativeStrength モデルのインスタンス作成を検証する."""
    rs = RelativeStrength(
        symbol="9988.HK",
        calculation_date=date(2024, 1, 15),
        change_63days=Decimal("15.50"),
        change_126days=Decimal("22.30"),
        change_189days=Decimal("18.75"),
        change_252days=Decimal("25.40"),
        relative_strength_score=Decimal("20.49"),
    )

    assert rs.symbol == "9988.HK"
    assert rs.calculation_date == date(2024, 1, 15)
    assert rs.change_63days == Decimal("15.50")
    assert rs.change_126days == Decimal("22.30")
    assert rs.change_189days == Decimal("18.75")
    assert rs.change_252days == Decimal("25.40")
    assert rs.relative_strength_score == Decimal("20.49")


def test_relative_strength_model_nullable_fields():
    """RelativeStrength の nullable フィールドが None で初期化できることを検証する."""
    rs = RelativeStrength(
        symbol="7203.T",
        calculation_date=date(2024, 1, 10),
        change_63days=None,
        change_126days=None,
        change_189days=None,
        change_252days=None,
        relative_strength_score=None,
    )

    assert rs.change_63days is None
    assert rs.change_126days is None
    assert rs.change_189days is None
    assert rs.change_252days is None
    assert rs.relative_strength_score is None


def test_relative_strength_model_repr():
    """RelativeStrength の __repr__ メソッドが正しい形式を返すことを検証する."""
    rs = RelativeStrength(
        symbol="9984.T",
        calculation_date=date(2024, 2, 1),
        relative_strength_score=Decimal("18.50"),
    )

    repr_str = repr(rs)

    assert "RelativeStrength" in repr_str
    assert "9984.T" in repr_str
    assert "2024-02-01" in repr_str
    assert "18.50" in repr_str


def test_relative_strength_model_tablename():
    """テーブル名が正しく設定されていることを検証する."""
    assert RelativeStrength.__tablename__ == "relative_strength"


def test_relative_strength_model_has_required_attributes():
    """モデルが必須属性を持つことを検証する."""
    assert hasattr(RelativeStrength, "symbol")
    assert hasattr(RelativeStrength, "calculation_date")
    assert hasattr(RelativeStrength, "change_63days")
    assert hasattr(RelativeStrength, "change_126days")
    assert hasattr(RelativeStrength, "change_189days")
    assert hasattr(RelativeStrength, "change_252days")
    assert hasattr(RelativeStrength, "relative_strength_score")


def test_relative_strength_model_has_timestamp_mixin():
    """TimestampMixin から継承されている属性を検証する."""
    assert hasattr(RelativeStrength, "created_at")
    assert hasattr(RelativeStrength, "updated_at")


def test_relative_strength_model_has_pk_mixin():
    """SerialPKMixin から継承されている属性を検証する."""
    assert hasattr(RelativeStrength, "id")
