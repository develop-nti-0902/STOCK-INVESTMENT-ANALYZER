"""latest_stocks_repositoryのユニットテスト."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.latest_stocks_repository import LatestStocksRepository


@pytest.fixture
def mock_session():
    """モックセッションを作成するフィクスチャ."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    """LatestStocksRepositoryインスタンスを作成するフィクスチャ."""
    return LatestStocksRepository(session=mock_session)


class TestLatestStocksRepository:
    """LatestStocksRepositoryのテストクラス."""

    @pytest.mark.asyncio
    async def test_get_latest_stock_by_symbol_success(
        self, repository, mock_session
    ):
        """正常系: 指定したシンボルの最新株価情報を取得できる."""
        symbol = "7203.T"

        mock_row = Mock()
        mock_row.id = 1
        mock_row.symbol = symbol
        mock_row.timestamp = "2026-01-22T00:00:00+00:00"
        mock_row.open = Decimal("1000.0000")
        mock_row.high = Decimal("1100.0000")
        mock_row.low = Decimal("950.0000")
        mock_row.close = Decimal("1050.0000")
        mock_row.adj_close = Decimal("1050.0000")
        mock_row.volume = 1000000

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_latest_stock_by_symbol(symbol)

        assert result is not None
        assert result["symbol"] == symbol
        assert result["close"] == Decimal("1050.0000")
        assert result["volume"] == 1000000
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_stock_by_symbol_not_found(
        self, repository, mock_session
    ):
        """異常系: 指定したシンボルが見つからない場合にNoneを返す."""
        symbol = "NOTFOUND"

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_latest_stock_by_symbol(symbol)

        assert result is None
        mock_session.execute.assert_called_once()
