"""抽象基底クラスの契約に関する単体テスト."""

import pytest

from app.services.core.converters.base_converter import BaseConverter
from app.services.core.fetchers.base_fetcher import BaseFetcher
from app.services.core.savers.base_saver import BaseSaver
from app.services.core.validators.base_validator import BaseValidator, ValidationResult


class TestAbstractClassInstantiation:
    """抽象クラスの直接インスタンス化不可を検証します."""

    def test_base_fetcher_instantiation_raises_type_error(self):
        """BaseFetcher は抽象メソッド未実装のため生成時に TypeError を送出します."""
        with pytest.raises(TypeError):
            BaseFetcher()  # type: ignore[abstract]

    def test_base_saver_instantiation_raises_type_error(self):
        """BaseSaver は抽象メソッド未実装のため生成時に TypeError を送出します."""
        with pytest.raises(TypeError):
            BaseSaver()  # type: ignore[abstract]

    def test_base_validator_instantiation_raises_type_error(self):
        """BaseValidator は抽象メソッド未実装のため生成時に TypeError を送出します."""
        with pytest.raises(TypeError):
            BaseValidator()  # type: ignore[abstract]

    def test_base_converter_instantiation_raises_type_error(self):
        """BaseConverter は抽象メソッド未実装のため生成時に TypeError を送出します."""
        with pytest.raises(TypeError):
            BaseConverter()  # type: ignore[abstract]


class TestPartialImplementation:
    """抽象メソッド未実装サブクラスの挙動を検証します."""

    def test_fetcher_partial_implementation_raises(self):
        """fetch_batch 未実装のサブクラスの生成が失敗することを検証します."""

        class PartialFetcher(BaseFetcher[str]):
            async def fetch(self, identifier: str, **kwargs) -> str:
                return identifier

        with pytest.raises(TypeError):
            PartialFetcher()  # type: ignore[abstract]

    def test_saver_partial_implementation_raises(self):
        """save_batch 未実装のサブクラスの生成が失敗することを検証します."""

        class PartialSaver(BaseSaver[dict]):  # noqa: D401
            async def save(self, data: dict, **kwargs) -> bool:  # noqa: D401
                return True

        with pytest.raises(TypeError):
            PartialSaver()  # type: ignore[abstract]

    def test_converter_partial_implementation_raises(self):
        """from_pydantic 未実装のサブクラスの生成が失敗することを検証します."""

        class PartialConverter(BaseConverter[dict]):  # noqa: D401
            def to_pydantic(self, data: dict) -> dict:  # noqa: D401
                return data

        with pytest.raises(TypeError):
            PartialConverter()  # type: ignore[abstract]

    def test_validator_partial_implementation_not_applicable(self):
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
