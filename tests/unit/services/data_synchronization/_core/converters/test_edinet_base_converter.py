"""Unit tests for edinet base converter."""

from datetime import date

from app.services.data_synchronization._core.converters.edinet_base_converter import (
    EdinetBaseConverter,
)


class DummyConverter(EdinetBaseConverter[dict]):
    """テスト用の EdinetBaseConverter の最小実装."""

    def _build_model(self, model_kwargs: dict) -> dict:
        """モデル構築を模擬する最小実装."""
        return model_kwargs


def test_to_decimal_and_fiscal_year_and_extract():
    """ヘルパー関数(to_decimal/fiscal_year/extract_metadata) の基本動作を検証する."""
    c = DummyConverter()
    assert c.to_decimal("123.45") is not None
    assert c.to_decimal(None) is None
    assert c.fiscal_year_from_period("2022-03-31") == 2022
    assert c.fiscal_year_from_period(date(2021, 12, 31)) == 2021
    meta = c.extract_metadata({"doc_id": "d", "sec_code": "s"})
    assert meta["doc_id"] == "d"
