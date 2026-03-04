"""Tests for MarketCategoryMasterRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.stock_master import MarketCategoryMaster
from app.repositories.market_data.stock_master import MarketCategoryMasterRepository


@pytest.mark.asyncio
async def test_market_category_master_repository_get_by_code():
    """MarketCategoryMasterRepository.get_by_code() のテスト."""
    mock_session = AsyncMock()
    market = MarketCategoryMaster(id=1, code="Prime", name="プライム市場")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=market)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = MarketCategoryMasterRepository(session=mock_session)
    result = await repo.get_by_code("Prime")

    assert result == market
    assert result.code == "Prime"
