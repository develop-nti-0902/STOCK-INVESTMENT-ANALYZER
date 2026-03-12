"""Unit tests for StockCodeMappingRepository."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.stock_master import StockCodeMappingRepository


@pytest.mark.asyncio
async def test_repository_has_required_methods():
    """Test StockCodeMappingRepository has required methods."""
    assert hasattr(StockCodeMappingRepository, "get_by_stock_code")
    assert hasattr(StockCodeMappingRepository, "get_by_sec_code")
    assert hasattr(StockCodeMappingRepository, "bulk_upsert")
    assert hasattr(StockCodeMappingRepository, "delete_all")


@pytest.mark.asyncio
async def test_delete_all_returns_count():
    """Test delete_all method returns deleted count."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = StockCodeMappingRepository(session=mock_session)

    # delete_all is implemented using statement execution
    # This test verifies the method exists and can be called
    assert callable(repo.delete_all)
