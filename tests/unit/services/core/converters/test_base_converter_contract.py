"""BaseConverter に関する契約テスト（抽象クラス挙動)."""

import pytest

from app.services.core.converters.base_converter import BaseConverter


def test_base_converter_instantiation_raises_type_error():
    """BaseConverter は抽象メソッド未実装のため生成時に TypeError を送出します."""
    with pytest.raises(TypeError):
        BaseConverter()  # type: ignore[abstract]


def test_converter_partial_implementation_raises():
    """from_pydantic 未実装のサブクラスの生成が失敗することを検証します."""

    class PartialConverter(BaseConverter[dict]):  # noqa: D401
        def to_pydantic(self, data: dict) -> dict:  # noqa: D401
            return data

    with pytest.raises(TypeError):
        PartialConverter()  # type: ignore[abstract]
