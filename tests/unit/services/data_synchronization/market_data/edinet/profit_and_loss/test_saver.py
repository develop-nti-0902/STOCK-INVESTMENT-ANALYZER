"""EdinetProfitAndLossSaver の単体テスト.

リポジトリ呼び出しはモック化して非同期挙動を検証する.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.services.data_synchronization.market_data.edinet.profit_and_loss.saver import (
    EdinetProfitAndLossSaver,
)


class _DummyModel:
    def __init__(self, id: int, **kwargs):
        self.id = id
        self.sec_code = kwargs.get("sec_code")
        self.edinet_document_id = kwargs.get("edinet_document_id")


class _DummyDocumentModel:
    def __init__(self, id: int, doc_id: str):
        self.id = id
        self.doc_id = doc_id


class _DummyDocumentRepo:
    def __init__(self, session):
        self._session = session

    async def create_or_get(self, **kwargs):
        # EdinetDocument をモック化して返す
        # sec_code + doc_idの組み合わせで特定の behavior をシミュレート
        doc_id = kwargs.get("doc_id", "D1")
        sec_code = kwargs.get("sec_code", "")

        # RAISE という sec_code の場合は特殊な ID を返す（失敗をシミュレート）
        mock_id = 888 if sec_code == "RAISE" else 999
        return _DummyDocumentModel(id=mock_id, doc_id=doc_id)


class _DummyRepo:
    def __init__(self, session):
        self._session = session

    async def upsert(self, data):
        # edinet_document_id が 888 の場合は失敗をシミュレート
        if data.get("edinet_document_id") == 888:
            raise RuntimeError("upsert failed")
        # model を返す
        return _DummyModel(id=123, edinet_document_id=data.get("edinet_document_id"))

    async def find_by_period(self, sec_code, period_end_date):
        if sec_code == "FOUND":
            return _DummyModel(id=1, sec_code=sec_code)
        return None

    async def find_latest_by_sec_code(self, sec_code):
        if sec_code == "LATEST":
            return _DummyModel(id=99, sec_code=sec_code)
        return None


class ConcreteSaver(EdinetProfitAndLossSaver):
    """テスト用のConcrete実装. 抽象メソッドを委譲実装する."""

    async def save(self, data, **kwargs):
        """単一保存を呼ぶテスト用実装."""
        return await self.save_single(data)


@pytest.mark.asyncio
async def test_validate_data_true_and_false():
    """validate_data の真偽を検証する."""
    saver = ConcreteSaver(session=None)

    good = {
        "doc_id": "D123456",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
    }
    bad = {"sec_code": None}

    assert await saver.validate_data(good) is True
    assert await saver.validate_data(bad) is False
    assert await saver.validate_data([]) is False


@pytest.mark.asyncio
async def test_save_single_success(monkeypatch):
    """save_single が正常に保存を返すことを検証する."""
    # リポジトリをモック化
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetProfitAndLossRepository",
        _DummyRepo,
    )
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetDocumentRepository",
        _DummyDocumentRepo,
    )

    saver = ConcreteSaver(session=None)

    data = {
        "doc_id": "D123456",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "operating_income": 1000.0,
        "eps": 50.0,
    }
    result = await saver.save_single(data)

    assert result is not None
    assert getattr(result, "id") == 123


@pytest.mark.asyncio
async def test_save_single_raises_on_empty_or_missing(monkeypatch):
    """空や不正データで例外が上がることを検証する."""
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetProfitAndLossRepository",
        _DummyRepo,
    )

    saver = ConcreteSaver(session=None)

    with pytest.raises(ValueError):
        await saver.save_single({})

    with pytest.raises(ValueError):
        await saver.save_single({"sec_code": "X"})


@pytest.mark.asyncio
async def test_save_batch_continues_on_error(monkeypatch):
    """バッチ処理で一件の失敗が継続されることを検証する."""
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetProfitAndLossRepository",
        _DummyRepo,
    )
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetDocumentRepository",
        _DummyDocumentRepo,
    )

    saver = ConcreteSaver(session=None)

    data_list = [
        {
            "doc_id": "D1",
            "sec_code": "GOOD",
            "submission_date": date(2024, 4, 1),
            "period_end_date": date(2024, 3, 31),
        },
        {
            "doc_id": "D2",
            "sec_code": "RAISE",
            "submission_date": date(2024, 4, 1),
            "period_end_date": date(2024, 3, 31),
        },
        {
            "doc_id": "D3",
            "sec_code": "GOOD2",
            "submission_date": date(2024, 4, 1),
            "period_end_date": date(2024, 3, 31),
        },
    ]

    results = await saver.save_batch(data_list)
    # RAISE の1件だけ失敗し、残りは成功しているはず
    assert len(results) == 2
    assert all(getattr(r, "id", None) is not None for r in results)


@pytest.mark.asyncio
async def test_exists_and_get_latest(monkeypatch):
    """exists と get_latest_by_sec_code の挙動を検証する."""
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetProfitAndLossRepository",
        _DummyRepo,
    )
    monkeypatch.setattr(
        "app.services.data_synchronization.market_data.edinet.profit_and_loss.saver.EdinetDocumentRepository",
        _DummyDocumentRepo,
    )

    saver = ConcreteSaver(session=None)

    exists_true = await saver.exists("FOUND", date(2024, 3, 31))
    exists_false = await saver.exists("NOT_FOUND", date(2024, 3, 31))

    assert exists_true is True
    assert exists_false is False

    latest = await saver.get_latest_by_sec_code("LATEST")
    assert latest is not None
    assert latest.sec_code == "LATEST"
