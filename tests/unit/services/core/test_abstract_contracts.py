"""
抽象基底クラス契約テスト

対象:
- BaseFetcher
- BaseSaver
- BaseValidator
- BaseConverter

検証内容:
1. 抽象クラスは直接インスタンス化できず TypeError を送出する
2. 抽象メソッドの一部未実装サブクラスも TypeError を送出する

注意:
Generic型境界は現時点で未設定(bound未使用)のため、型境界テストはスキップ。
"""

import pytest

from app.services.core.converters.base_converter import BaseConverter
from app.services.core.fetchers.base_fetcher import BaseFetcher
from app.services.core.savers.base_saver import BaseSaver
from app.services.core.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class TestAbstractClassInstantiation:
    """抽象クラス直接インスタンス化不可テスト"""

    def test_base_fetcher_instantiation_raises_type_error(self):
        """BaseFetcherは抽象メソッド未実装のため直接生成不可"""
        with pytest.raises(TypeError):
            BaseFetcher()  # type: ignore[abstract]

    def test_base_saver_instantiation_raises_type_error(self):
        """BaseSaverは抽象メソッド未実装のため直接生成不可"""
        with pytest.raises(TypeError):
            BaseSaver()  # type: ignore[abstract]

    def test_base_validator_instantiation_raises_type_error(self):
        """BaseValidatorは抽象メソッド未実装のため直接生成不可"""
        with pytest.raises(TypeError):
            BaseValidator()  # type: ignore[abstract]

    def test_base_converter_instantiation_raises_type_error(self):
        """BaseConverterは抽象メソッド未実装のため直接生成不可"""
        with pytest.raises(TypeError):
            BaseConverter()  # type: ignore[abstract]


class TestPartialImplementation:
    """抽象メソッド未実装サブクラスの挙動テスト"""

    def test_fetcher_partial_implementation_raises(self):
        """fetch_batch未実装サブクラスは生成不可"""

        class PartialFetcher(BaseFetcher[str]):
            async def fetch(self, identifier: str, **kwargs) -> str:
                return identifier

        with pytest.raises(TypeError):
            PartialFetcher()  # type: ignore[abstract]

    def test_saver_partial_implementation_raises(self):
        """save_batch未実装サブクラスは生成不可"""

        class PartialSaver(BaseSaver[dict]):  # noqa: D401
            async def save(self, data: dict, **kwargs) -> bool:  # noqa: D401
                return True

        with pytest.raises(TypeError):
            PartialSaver()  # type: ignore[abstract]

    def test_converter_partial_implementation_raises(self):
        """from_pydantic未実装サブクラスは生成不可"""

        class PartialConverter(BaseConverter[dict]):  # noqa: D401
            def to_pydantic(self, data: dict) -> dict:  # noqa: D401
                return data

        with pytest.raises(TypeError):
            PartialConverter()  # type: ignore[abstract]

    def test_validator_partial_implementation_not_applicable(self):
        """
        BaseValidatorは validate が唯一の抽象メソッドのため
        部分実装パターン（validate以外のみ実装）は存在しないことを明示する。
        ここではダミー検証: validate未実装ならTypeError、実装すれば生成可。
        """

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
