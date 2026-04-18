"""Nikkei225ComponentRepositoryのユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.nikkei225.nikkei225_components_repository import (
    Nikkei225ComponentRepository,
)


@pytest.fixture
def mock_session():
    """モックDBセッション."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session):
    """Nikkei225ComponentRepositoryインスタンス."""
    return Nikkei225ComponentRepository(session=mock_session)


class TestUpsertBatch:
    """upsert_batch のテスト."""

    @pytest.mark.asyncio
    async def test_upsert_batch_empty_list(self, repo):
        """空リストを渡した場合、空リストが返り DB は呼び出されないこと."""
        result = await repo.upsert_batch([])

        assert result == []
        repo.session.execute.assert_not_called()
        repo.session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_batch_calls_execute(self, repo):
        """有効なデータを渡した場合、execute と flush が呼ばれること."""
        data = [
            {
                "stock_code": "7203",
                "price_adjustment_factor": 50.0,
                "effective_date": "2026-04-18",
            }
        ]

        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 1,
            "stock_code": "7203",
            "price_adjustment_factor": 50.0,
            "effective_date": "2026-04-18",
            "created_at": None,
            "updated_at": None,
        }
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [mock_row]
        repo.session.execute = AsyncMock(return_value=mock_result)

        result = await repo.upsert_batch(data)

        repo.session.execute.assert_called_once()
        repo.session.flush.assert_called_once()
        assert len(result) == 1


class TestFindByCode:
    """find_by_code のテスト."""

    @pytest.mark.asyncio
    async def test_find_by_code_returns_none_when_not_found(self, repo):
        """存在しないコードを検索した場合、None が返ること."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repo.session.execute = AsyncMock(return_value=mock_result)

        result = await repo.find_by_code("9999")

        assert result is None
        repo.session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_code_returns_component_when_found(self, repo):
        """存在するコードを検索した場合、コンポーネントが返ること."""
        mock_component = MagicMock()
        mock_component.stock_code = "7203"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_component
        repo.session.execute = AsyncMock(return_value=mock_result)

        result = await repo.find_by_code("7203")

        assert result is not None
        assert result.stock_code == "7203"
        repo.session.execute.assert_called_once()
