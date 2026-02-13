"""BaseValidator に関する契約テスト（抽象クラス挙動)."""

import pytest

from app.services.core.validators.base_validator import BaseValidator, ValidationResult


def test_base_validator_instantiation_raises_type_error():
    """BaseValidator は抽象メソッド未実装のため生成時に TypeError を送出します."""
    with pytest.raises(TypeError):
        BaseValidator()  # type: ignore[abstract]


def test_validator_partial_implementation_not_applicable():
    """BaseValidator の部分実装パターンが該当しないことを検証します."""

    class PartialValidator(BaseValidator):  # noqa: D401
        pass

    with pytest.raises(TypeError):
        PartialValidator()  # type: ignore[abstract]

    class ConcreteValidator(BaseValidator):
        def validate(self, data):
            return ValidationResult(True)

    # 実装済みなら生成可能
    instance = ConcreteValidator()
    assert instance is not None
