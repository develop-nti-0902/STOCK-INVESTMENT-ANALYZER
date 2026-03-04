"""Tests for Sector33MasterRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.stock_master import Sector33Master
from app.repositories.market_data.stock_master import Sector33MasterRepository


@pytest.mark.asyncio
async def test_sector_33_master_repository_get_by_code():
    """Sector33MasterRepository.get_by_code() のテスト."""
    mock_session = AsyncMock()
    sector = Sector33Master(id=1, code="08", name="水産・農林業")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=sector)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = Sector33MasterRepository(session=mock_session)
    result = await repo.get_by_code("08")

    assert result == sector
    assert result.code == "08"
