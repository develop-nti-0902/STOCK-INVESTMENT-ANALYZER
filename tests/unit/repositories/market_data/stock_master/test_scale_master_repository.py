"""Tests for ScaleMasterRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.stock_master import ScaleMaster
from app.repositories.market_data.stock_master import ScaleMasterRepository


@pytest.mark.asyncio
async def test_scale_master_repository_get_by_code():
    """ScaleMasterRepository.get_by_code() テスト."""
    mock_session = AsyncMock()
    scale = ScaleMaster(id=1, code="L", name="Large")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=scale)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = ScaleMasterRepository(session=mock_session)
    result = await repo.get_by_code("L")

    assert result == scale
    assert result.code == "L"
