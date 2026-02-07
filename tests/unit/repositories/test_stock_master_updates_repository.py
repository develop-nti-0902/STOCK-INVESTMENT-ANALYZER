"""`StockMasterUpdatesRepository` の単体テスト集."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_master_updates import StockMasterUpdates
from app.repositories.stock_master_updates_repository import StockMasterUpdatesRepository


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


@pytest.mark.asyncio
async def test_update_status_updates_fields():
    """update_status がフィールドを更新して flush することを検証します."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.flush = AsyncMock()

    # 既存インスタンスを用意し、get() が返すようにする
    existing = StockMasterUpdates(
        update_type="refresh",
        total_stocks=5,
        status="running",
    )

    fake_result = MagicMock()
    fake_result.scalar_one_or_none.return_value = existing
    mock_session.execute = AsyncMock(return_value=fake_result)

    repo = StockMasterUpdatesRepository(session=mock_session)

    updated = await repo.update_status(existing.id, "success", {"added_stocks": 2})

    # flush が呼ばれ、既存オブジェクトの属性が更新されていること
    mock_session.flush.assert_awaited_once()
    assert updated is not None
    assert updated.status == "success"
    assert getattr(updated, "added_stocks") == 2


@pytest.mark.asyncio
async def test_delete_by_reset_executes_delete_and_returns_count():
    """delete_by_reset が削除数を返すことを検証します."""
    mock_session = AsyncMock(spec=AsyncSession)

    fake_result = MagicMock()
    fake_result.rowcount = 3
    mock_session.execute = AsyncMock(return_value=fake_result)

    repo = StockMasterUpdatesRepository(session=mock_session)

    deleted = await repo.delete_by_reset()

    mock_session.execute.assert_awaited()
    assert deleted == 3
