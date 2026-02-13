"""EdinetStockDividendSaver の単体テスト（リポジトリはモック化）."""

from __future__ import annotations

import pytest

from app.services.market_data.edinet.stock_dividend.saver import EdinetStockDividendSaver


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
    saver = ConcreteSaver(session=None)

    good = {"sec_code": "7203", "period_end_date": "2024-03-31"}
    bad = {"sec_code": None}

    assert await saver.validate_data(good) is True
    assert await saver.validate_data(bad) is False
    assert await saver.validate_data([]) is False


@pytest.mark.asyncio
async def test_save_single_success(monkeypatch):
    """save_single が正しく保存してモデルを返すことを確認する."""
    monkeypatch.setattr(
        "app.services.market_data.edinet.stock_dividend.saver.EdinetStockDividendRepository",
        _DummyRepo,
    )

    saver = ConcreteSaver(session=None)

    data = {"sec_code": "7203", "period_end_date": "2024-03-31"}
    result = await saver.save_single(data)

    assert result is not None
    assert getattr(result, "id") == 123
    assert result.sec_code == "7203"


@pytest.mark.asyncio
async def test_save_single_raises_on_empty_or_missing():
    """空データや必須キー欠如で ValueError を発生させることを検証する."""
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(
            "app.services.market_data.edinet.stock_dividend.saver.EdinetStockDividendRepository",
            _DummyRepo,
        )

        saver = ConcreteSaver(session=None)

        with pytest.raises(ValueError):
            await saver.save_single({})

        with pytest.raises(ValueError):
            await saver.save_single({"sec_code": "X"})
    finally:
        monkeypatch.undo()


@pytest.mark.asyncio
async def test_save_batch_continues_on_error(monkeypatch):
    """バッチ保存で一つの失敗があっても処理が継続することを確認する."""
    monkeypatch.setattr(
        "app.services.market_data.edinet.stock_dividend.saver.EdinetStockDividendRepository",
        _DummyRepo,
    )

    saver = ConcreteSaver(session=None)

    data_list = [
        {"sec_code": "GOOD", "period_end_date": "2024-03-31"},
        {"sec_code": "RAISE", "period_end_date": "2024-03-31"},
        {"sec_code": "GOOD2", "period_end_date": "2024-03-31"},
    ]

    results = await saver.save_batch(data_list)
    assert len(results) == 2
    assert all(getattr(r, "id", None) is not None for r in results)


@pytest.mark.asyncio
async def test_exists_and_get_latest(monkeypatch):
    """exists と get_latest_by_sec_code の挙動を検証する."""
    monkeypatch.setattr(
        "app.services.market_data.edinet.stock_dividend.saver.EdinetStockDividendRepository",
        _DummyRepo,
    )

    saver = ConcreteSaver(session=None)

    exists_true = await saver.exists("FOUND", "2024-03-31")
    exists_false = await saver.exists("NOT_FOUND", "2024-03-31")

    assert exists_true is True
    assert exists_false is False

    latest = await saver.get_latest_by_sec_code("LATEST")
    assert latest is not None
    assert latest.sec_code == "LATEST"
