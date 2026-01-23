from unittest.mock import AsyncMock

import pytest

from app.exceptions.business import ServiceError
from app.services.views.latest_stocks.service import LatestStocksService


@pytest.mark.asyncio
async def test_get_latest_stock_success():
    """正常系: リポジトリがデータを返すと Pydantic レスポンスが返却される。"""
    # arrange
    payload = {
        "id": 1,
        "symbol": "7203.T",
        "timestamp": "2026-01-22T00:00:00+00:00",
        "open": 1000.0,
        "high": 1100.0,
        "low": 950.0,
        "close": 1050.0,
        "adj_close": 1050.0,
        "volume": 1000000,
    }

    repo = AsyncMock()
    repo.get_latest_stock_by_symbol.return_value = payload

    svc = LatestStocksService(repository=repo)

    # act
    res = await svc.get_latest_stock("7203.T")

    # assert
    assert res.symbol == payload["symbol"]
    assert int(res.id) == payload["id"]
    assert res.close == pytest.approx(payload["close"])  # numeric compare
    repo.get_latest_stock_by_symbol.assert_awaited_once_with("7203.T")


@pytest.mark.asyncio
async def test_get_latest_stock_not_found_raises_service_error():
    """異常系: リポジトリが None を返すと ServiceError を送出する。"""
    repo = AsyncMock()
    repo.get_latest_stock_by_symbol.return_value = None

    svc = LatestStocksService(repository=repo)

    with pytest.raises(ServiceError):
        await svc.get_latest_stock("NOTFOUND")


@pytest.mark.asyncio
async def test_get_latest_stock_repository_raises_wrapped_as_service_error():
    """異常系: リポジトリ内の一般例外は ServiceError に変換される。"""
    repo = AsyncMock()
    repo.get_latest_stock_by_symbol.side_effect = RuntimeError("boom")

    svc = LatestStocksService(repository=repo)

    with pytest.raises(ServiceError):
        await svc.get_latest_stock("7203.T")
