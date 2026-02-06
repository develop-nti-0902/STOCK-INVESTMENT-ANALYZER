import pytest

from app.api.v1 import stock_master as stock_master_module
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError


class FakeService:
    def __init__(
        self,
        *,
        fetch_and_store_result=0,
        symbols=None,
        market_symbols=None,
        reset_result=0,
        raise_on=None
    ):
        self._fetch_and_store_result = fetch_and_store_result
        self._symbols = symbols or ["7203", "6758"]
        self._market_symbols = market_symbols
        self._reset_result = reset_result
        self._raise_on = raise_on or set()

    async def fetch_and_store(self, batch_size: int = 500):
        if "fetch_and_store" in self._raise_on:
            raise RuntimeError("fetch failed")
        return self._fetch_and_store_result

    async def fetch_and_save(self, *args, **kwargs):
        """互換性のためのエイリアスメソッド。内部実装は `fetch_and_store` を使う。"""
        return await self.fetch_and_store(*args, **kwargs)

    async def refresh_stock_master(self, batch_size: int = 500):
        # refresh_stock_master または fetch_and_store が失敗する設定なら例外を発生
        if "refresh_stock_master" in self._raise_on or "fetch_and_store" in self._raise_on:
            raise RuntimeError("refresh failed")
        return self._fetch_and_store_result

    async def get_all_active_symbols(self):
        if "get_all_active_symbols" in self._raise_on:
            raise RuntimeError("symbols fail")
        return self._symbols

    async def get_symbols_by_market(self, market: str):
        if "get_symbols_by_market" in self._raise_on:
            raise RuntimeError("market fail")
        # allow explicit override for tests
        if self._market_symbols is not None:
            return self._market_symbols
        return [s for s in self._symbols if s]

    async def reset_stock_master(self):
        if "reset_stock_master" in self._raise_on:
            raise RuntimeError("reset fail")
        return self._reset_result


@pytest.mark.asyncio
async def test_refresh_stock_master_success():
    # Arrange
    service = FakeService(fetch_and_store_result=5)

    # Act
    resp = await stock_master_module.fetch_stock_master(service=service)

    # Assert
    assert resp.updated_count == 5
    assert "Stock master fetch completed" in resp.message


@pytest.mark.asyncio
async def test_refresh_stock_master_failure_raises_500():
    # Arrange
    service = FakeService(raise_on={"fetch_and_store"})

    # Act / Assert
    with pytest.raises(ServiceError) as exc:
        await stock_master_module.fetch_stock_master(service=service)

    assert exc.value.status_code == 500
    assert "Failed to fetch stock master" in exc.value.message


@pytest.mark.asyncio
async def test_get_all_active_symbols_success():
    # Arrange
    service = FakeService(symbols=["1001", "2002"])

    # Act
    resp = await stock_master_module.get_all_active_symbols(service=service)

    # Assert
    assert resp.count == 2
    assert resp.symbols == ["1001", "2002"]


@pytest.mark.asyncio
async def test_get_all_active_symbols_failure_raises_500():
    # Arrange
    service = FakeService(raise_on={"get_all_active_symbols"})

    # Act / Assert
    with pytest.raises(ServiceError) as exc:
        await stock_master_module.get_all_active_symbols(service=service)

    assert exc.value.status_code == 500
    assert "Failed to retrieve stock symbols" in exc.value.message


@pytest.mark.asyncio
async def test_get_symbols_by_market_not_found_returns_404():
    # Arrange: service returns empty list for market
    service = FakeService(market_symbols=[])

    # Act / Assert
    with pytest.raises(RecordNotFoundError) as exc:
        await stock_master_module.get_symbols_by_market("Prime", service=service)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_symbols_by_market_failure_raises_500():
    # Arrange
    service = FakeService(raise_on={"get_symbols_by_market"})

    # Act / Assert
    with pytest.raises(ServiceError) as exc:
        await stock_master_module.get_symbols_by_market("Prime", service=service)

    assert exc.value.status_code == 500
    assert "Failed to retrieve stock symbols" in exc.value.message


@pytest.mark.asyncio
async def test_reset_stock_master_success():
    # Arrange
    service = FakeService(reset_result=10)

    # Act
    resp = await stock_master_module.reset_stock_master(service=service)

    # Assert
    assert resp.deleted_count == 10
    assert "Stock master reset completed" in resp.message


@pytest.mark.asyncio
async def test_reset_stock_master_failure_raises_500():
    # Arrange
    service = FakeService(raise_on={"reset_stock_master"})

    # Act / Assert
    with pytest.raises(ServiceError) as exc:
        await stock_master_module.reset_stock_master(service=service)

    assert exc.value.status_code == 500
    assert "Failed to reset stock master" in exc.value.message
