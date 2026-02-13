"""BaseFetcher に関する契約テスト（抽象クラス挙動)."""

import pytest

from app.services.core.fetchers.base_fetcher import BaseFetcher


def test_base_fetcher_instantiation_raises_type_error():
    """BaseFetcher は抽象メソッド未実装のため生成時に TypeError を送出します."""
    with pytest.raises(TypeError):
        BaseFetcher()  # type: ignore[abstract]


def test_fetcher_partial_implementation_raises():
    """fetch_batch 未実装のサブクラスの生成が失敗することを検証します."""

    class PartialFetcher(BaseFetcher[str]):
        async def fetch(self, identifier: str, **kwargs) -> str:
            return identifier

    with pytest.raises(TypeError):
        PartialFetcher()  # type: ignore[abstract]
