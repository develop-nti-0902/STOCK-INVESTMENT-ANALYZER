import pandas as pd
import pytest
from fastapi import HTTPException

from app.api.v1.stock_data import get_stock_data


class _MockResult:
    def __init__(self, df: pd.DataFrame | None):
        self.data = df


class _MockService:
    def __init__(self, result: _MockResult | None):
        self._result = result

    async def get_stock_data(self, *args, **kwargs):
        return self._result


@pytest.mark.asyncio
async def test_get_stock_data_success_and_nan_conversion():
    df = pd.DataFrame(
        [
            {
                "trade_date": pd.to_datetime("2025-01-01"),
                "open": 100.0,
                "close": 110.0,
            },
            {
                "trade_date": pd.to_datetime("2025-01-02"),
                "open": float("nan"),
                "close": 115.0,
            },
        ]
    )

    service = _MockService(_MockResult(df))

    resp = await get_stock_data(symbol="TEST", service=service, limit=None)

    assert resp["symbol"] == "TEST"
    assert resp["count"] == 2

    records = resp["data"]
    assert records[0]["open"] == 100.0
    assert records[1]["open"] is None
    assert isinstance(records[0]["trade_date"], str)
    assert records[0]["trade_date"].startswith("2025-01-01")


@pytest.mark.asyncio
async def test_get_stock_data_with_limit_applies_head():
    dates = pd.date_range("2025-01-01", periods=5)
    df = pd.DataFrame({"trade_date": dates, "open": range(5)})

    service = _MockService(_MockResult(df))

    resp = await get_stock_data(symbol="LIM", service=service, limit=3)

    assert resp["count"] == 3
    assert len(resp["data"]) == 3
    assert resp["data"][0]["open"] == 0


@pytest.mark.asyncio
async def test_get_stock_data_raises_404_on_none_or_empty():
    service_none = _MockService(None)
    with pytest.raises(HTTPException) as excinfo:
        await get_stock_data(symbol="X", service=service_none)
    assert excinfo.value.status_code == 404

    service_data_none = _MockService(_MockResult(None))
    with pytest.raises(HTTPException) as excinfo2:
        await get_stock_data(symbol="Y", service=service_data_none)
    assert excinfo2.value.status_code == 404

    empty_df = pd.DataFrame()
    service_empty = _MockService(_MockResult(empty_df))
    with pytest.raises(HTTPException) as excinfo3:
        await get_stock_data(symbol="Z", service=service_empty)
    assert excinfo3.value.status_code == 404
