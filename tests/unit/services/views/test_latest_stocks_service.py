"""latest_stocks_serviceのユニットテスト."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.exceptions.business import ServiceError
from app.repositories.latest_stocks_repository import LatestStocksRepository
from app.schemas.views import LatestStockResponse
from app.services.views.latest_stocks_service import LatestStocksService


@pytest.fixture
def mock_repository():
    """モックリポジトリを作成するフィクスチャ."""
    return Mock(spec=LatestStocksRepository)


@pytest.fixture
def service(mock_repository):
    """LatestStocksServiceインスタンスを作成するフィクスチャ."""
    return LatestStocksService(repository=mock_repository)


class TestLatestStocksService:
    """LatestStocksServiceのテストクラス."""

    @pytest.mark.asyncio
    async def test_get_latest_stock_success(self, service, mock_repository):
        """正常系: 指定したシンボルの最新株価情報を取得できる."""
        symbol = "7203.T"
        mock_data = {
            "id": 1,
            "symbol": symbol,
            "timestamp": "2026-01-22T00:00:00+00:00",
            "open": Decimal("1000.0000"),
            "high": Decimal("1100.0000"),
            "low": Decimal("950.0000"),
            "close": Decimal("1050.0000"),
            "adj_close": Decimal("1050.0000"),
            "volume": 1000000,
        }
        mock_repository.get_latest_stock_by_symbol = AsyncMock(
            return_value=mock_data
        )

        result = await service.get_latest_stock(symbol)

        assert isinstance(result, LatestStockResponse)
        assert result.symbol == symbol
        assert result.close == Decimal("1050.0000")
        mock_repository.get_latest_stock_by_symbol.assert_called_once_with(
            symbol
        )

    @pytest.mark.asyncio
    async def test_get_latest_stock_not_found(self, service, mock_repository):
        """異常系: 指定したシンボルが見つからない場合にServiceErrorが発生する."""
        symbol = "NOTFOUND"
        mock_repository.get_latest_stock_by_symbol = AsyncMock(
            return_value=None
        )

        with pytest.raises(ServiceError) as exc_info:
            await service.get_latest_stock(symbol)

        assert "not found" in str(exc_info.value).lower()
        mock_repository.get_latest_stock_by_symbol.assert_called_once_with(
            symbol
        )

    @pytest.mark.asyncio
    async def test_get_latest_stock_repository_exception(
        self, service, mock_repository
    ):
        """異常系: リポジトリで例外が発生した場合にServiceErrorが発生する."""
        symbol = "7203.T"
        mock_repository.get_latest_stock_by_symbol = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(ServiceError) as exc_info:
            await service.get_latest_stock(symbol)

        assert "Failed to get latest stock" in str(exc_info.value)
        mock_repository.get_latest_stock_by_symbol.assert_called_once_with(
            symbol
        )
