"""Tests for Sector17MasterRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.stock_master import Sector17Master
from app.repositories.market_data.stock_master import Sector17MasterRepository


@pytest.mark.asyncio
async def test_sector_17_master_repository_get_by_code():
    """Sector17MasterRepository.get_by_code() のテスト."""
    mock_session = AsyncMock()
    sector = Sector17Master(id=1, code="1", name="水産物・農産物")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=sector)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = Sector17MasterRepository(session=mock_session)
    result = await repo.get_by_code("1")

    assert result == sector
    assert result.code == "1"
