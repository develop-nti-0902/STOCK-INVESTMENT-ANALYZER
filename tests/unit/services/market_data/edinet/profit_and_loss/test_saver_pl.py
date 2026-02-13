"""EdinetProfitAndLossSaver の単体テスト（profit_and_loss 固有）."""

from __future__ import annotations

import pytest

from app.services.market_data.edinet.profit_and_loss.saver import EdinetProfitAndLossSaver


class _DummyModel:
    def __init__(self, id: int, sec_code: str):
        self.id = id
        self.sec_code = sec_code


class _DummyRepo:
    def __init__(self, session):
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


class ConcreteSaver(EdinetProfitAndLossSaver):
    """テスト用のConcrete実装."""

    async def save(self, data, **kwargs):
        """単一保存を呼ぶテスト用実装."""
        return await self.save_single(data)


@pytest.mark.asyncio
async def test_validate_data_true_and_false():
    """validate_data の真偽を検証する."""
    saver = ConcreteSaver(session=None)

    good = {"sec_code": "7203", "period_end_date": "2024-03-31"}
    bad = {"sec_code": None}

    assert await saver.validate_data(good) is True
    assert await saver.validate_data(bad) is False
    assert await saver.validate_data([]) is False
