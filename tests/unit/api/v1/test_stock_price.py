"""Unit tests for `app.api.v1.stock_price` endpoints."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.v1 import stock_price as sp_mod
from app.exceptions.business import ServiceError
from app.exceptions.validation import FieldValidationError


class DummyService:
    """シンプルなモックサービス実装 (テスト用)."""

    def __init__(self, *, rows=None, fetch_results=None, summary=None, delete_count=0):
        """初期化."""
        self._rows = rows or []
        self._fetch_results = fetch_results or []
        self._summary = summary or {}
        self._delete_count = delete_count

    async def get_stock_data_from_db(self, **kwargs):
        """DB 取得を模倣して `rows` を返す."""
        return self._rows

    async def fetch_and_save(self, *, symbols, timeframe, period=None):
        """fetch_and_save のモック実装."""
        return self._fetch_results

    async def fetch_and_save_for_all_jpx(
        self, *, timeframe, market=None, batch_size=100, period=None
    ):
        """JPX一括フェッチのモック実装."""
        return self._summary

    async def delete_all_for_timeframe(self, db, timeframe):
        """指定時間軸の全削除モック実装."""
        return self._delete_count


@pytest.mark.asyncio
async def test_get_stock_price_data_parses_dates_and_returns_list():
    """start/end の文字列をパースしてデータが返ることを確認する."""
    rows = [
        {
            "symbol": "7203.T",
            "timestamp": datetime(2024, 1, 1, 9, 0, 0),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "adj_close": None,
            "volume": 1000,
        }
    ]
    svc = DummyService(rows=rows)

    resp = await sp_mod.get_stock_price_data(
        symbol="7203.T",
        timeframe="1d",
        start="2024-01-01",
        end="2024-01-02",
        limit=10,
        offset=0,
        service=svc,
        db=None,
    )

    assert resp.symbol == "7203.T"
    assert resp.count == 1
    assert resp.data[0].open == 100.0


@pytest.mark.asyncio
async def test_get_stock_price_data_invalid_date_raises():
    """不正な日付文字列で FieldValidationError が発生すること."""
    svc = DummyService(rows=[])
    with pytest.raises(FieldValidationError):
        await sp_mod.get_stock_price_data(
            symbol="7203.T",
            timeframe="1d",
            start="invalid-date",
            end=None,
            limit=10,
            offset=0,
            service=svc,
            db=None,
        )


@pytest.mark.asyncio
async def test_get_stock_price_service_error_wrapped():
    """service 側の例外が ServiceError にラップされること."""

    class BadService(DummyService):
        async def get_stock_data_from_db(self, **kwargs):
            raise RuntimeError("boom")

    svc = BadService()
    with pytest.raises(ServiceError):
        await sp_mod.get_stock_price_data(
            symbol="7203.T",
            timeframe="1d",
            start=None,
            end=None,
            limit=10,
            offset=0,
            service=svc,
            db=None,
        )


@pytest.mark.asyncio
async def test_fetch_and_save_stock_price_maps_result():
    """fetch_and_save の戻り値が FetchResponse にマッピングされること."""
    item = SimpleNamespace(
        symbol="7203.T",
        timeframe="1d",
        success=True,
        records_processed=2,
        records_saved=2,
        errors=None,
        warnings=None,
    )
    svc = DummyService(fetch_results=[item])

    req = sp_mod.FetchRequest(symbols=["7203.T"], timeframe="1d")
    resp = await sp_mod.fetch_and_save_stock_price(req=req, service=svc)

    assert len(resp.results) == 1
    assert resp.results[0].symbol == "7203.T"
    assert resp.results[0].success is True


@pytest.mark.asyncio
async def test_fetch_and_save_raises_service_error_on_fail():
    """fetch_and_save が例外を投げたら ServiceError になること."""

    class BadService(DummyService):
        async def fetch_and_save(self, **kwargs):
            raise Exception("fail")

    svc = BadService()
    req = sp_mod.FetchRequest(symbols=["7203.T"], timeframe="1d")
    with pytest.raises(ServiceError):
        await sp_mod.fetch_and_save_stock_price(req=req, service=svc)


@pytest.mark.asyncio
async def test_execute_jpx_batch_maps_summary():
    """fetch_and_save_for_all_jpx のサマリが BatchResponse に変換されること."""
    summary = {"total": 10, "success": 8, "failed": 2, "errors": [], "elapsed_time": 1.23}
    svc = DummyService(summary=summary)
    req = sp_mod.BatchRequest(timeframe="1d")

    resp = await sp_mod.execute_jpx_batch(req=req, service=svc)
    assert resp.total == 10
    assert resp.success == 8
    assert resp.failed == 2


@pytest.mark.asyncio
async def test_execute_jpx_batch_raises_service_error_on_fail():
    """fetch_and_save_for_all_jpx が例外時に ServiceError を送出すること."""

    class BadService(DummyService):
        async def fetch_and_save_for_all_jpx(self, **kwargs):
            raise RuntimeError("batch fail")

    svc = BadService()
    req = sp_mod.BatchRequest(timeframe="1d")
    with pytest.raises(ServiceError):
        await sp_mod.execute_jpx_batch(req=req, service=svc)


@pytest.mark.asyncio
async def test_delete_all_stock_price_data_success():
    """delete_all_for_timeframe の戻り値が DeleteAllResponse に反映されること."""
    svc = DummyService(delete_count=42)
    resp = await sp_mod.delete_all_stock_price_data(timeframe="1d", service=svc, db=None)
    assert resp.deleted_count == 42


@pytest.mark.asyncio
async def test_delete_all_stock_price_data_field_validation_propagates():
    """delete_all_for_timeframe が FieldValidationError を送出する場合は透過すること."""

    class BadService(DummyService):
        async def delete_all_for_timeframe(self, db, timeframe):
            raise FieldValidationError(message="invalid timeframe")

    svc = BadService()
    with pytest.raises(FieldValidationError):
        await sp_mod.delete_all_stock_price_data(timeframe="bad", service=svc, db=None)
