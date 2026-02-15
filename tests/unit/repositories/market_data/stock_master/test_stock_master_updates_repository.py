"""`StockMasterUpdatesRepository` の単体テスト集."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.stock_master import StockMasterUpdatesRepository


@pytest.mark.asyncio
async def test_create_summary_calls_add_and_flush():
    """create_summary が session.add/flush を呼ぶことを検証します."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.flush = AsyncMock()

    repo = StockMasterUpdatesRepository(session=mock_session)

    data = {
        "update_type": "refresh",
        "total_stocks": 10,
        "status": "running",
    }

    result = await repo.create_summary(data)

    # session.add と flush が呼ばれていること
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

    # 生成されたインスタンスに渡した値が設定されていること
    assert getattr(result, "update_type") == "refresh"
    assert getattr(result, "total_stocks") == 10
    assert getattr(result, "status") == "running"
