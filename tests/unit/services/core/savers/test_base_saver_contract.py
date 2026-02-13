"""BaseSaver に関する契約テスト（抽象クラス挙動)."""

import pytest

from app.services.core.savers.base_saver import BaseSaver


def test_base_saver_instantiation_raises_type_error():
    """BaseSaver は抽象メソッド未実装のため生成時に TypeError を送出します."""
    with pytest.raises(TypeError):
        BaseSaver()  # type: ignore[abstract]


def test_saver_partial_implementation_raises():
    """save_batch 未実装のサブクラスの生成が失敗することを検証します."""

    class PartialSaver(BaseSaver[dict]):  # noqa: D401
        async def save(self, data: dict, **kwargs) -> bool:  # noqa: D401
            return True

    with pytest.raises(TypeError):
        PartialSaver()  # type: ignore[abstract]
