"""EdinetStockDividendSaver の単体テスト（リポジトリはモック化）."""

from __future__ import annotations

import pytest

from app.services.data_synchronization.market_data.edinet.stock_dividend.saver import (
    EdinetStockDividendSaver,
)


class _DummyModel:
    def __init__(self, id: int, sec_code: str):
        """ダミーモデル（テスト用）."""
        self.id = id
        self.sec_code = sec_code


class _DummyRepo:
    def __init__(self, session):
        """ダミーリポジトリ（テスト用）."""
        self._session = session

    async def upsert(self, data):
        if data.get("sec_code") == "RAISE":
            raise RuntimeError("upsert failed")
        return _DummyModel(id=123, sec_code=data.get("sec_code"))

    async def find_by_period(self, sec_code, period_end_date):
        if sec_code == "FOUND":
            return _DummyModel(id=1, sec_code=sec_code)
        return None

    async def find_latest_by_sec_code(self, sec_code):
        if sec_code == "LATEST":
            return _DummyModel(id=99, sec_code=sec_code)
        return None


class ConcreteSaver(EdinetStockDividendSaver):
    """テスト用の ConcreteSaver 実装クラス."""

    async def save(self, data, **kwargs):
        """ConcreteSaver の save 実装（テスト用）."""
        return await self.save_single(data)


@pytest.mark.asyncio
async def test_validate_data_true_and_false():
    """validate_data が真と偽を正しく返すことを検証する."""
    concrete_saver = ConcreteSaver(session=None)

    # Test true case
    assert concrete_saver.validate_data_sync({"sec_code": "7203", "period_end_date": "2024-03-31"})

    # Test false case
    assert not concrete_saver.validate_data_sync({"sec_code": "7203"})
    assert not concrete_saver.validate_data_sync("not a dict")
