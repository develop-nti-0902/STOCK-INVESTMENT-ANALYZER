"""DividendYieldMonitoringRepository の基本構成を検証するテスト。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.monitoring.dividend_yield_monitoring import DividendYieldMonitoring
from app.repositories.monitoring.dividend_yield_monitoring_repository import (
    DividendYieldMonitoringRepository,
)


class DummySession(SimpleNamespace):
    """DBセッションを模したプレースホルダー。"""

    pass


def test_repository_binds_model() -> None:
    """リポジトリが正しいモデルをバインドしていることを確認する。"""
    session = DummySession()
    repo = DividendYieldMonitoringRepository(session=session)  # type: ignore[arg-type]
    assert repo.model is DividendYieldMonitoring


@pytest.mark.asyncio
async def test_bulk_upsert_exceeds_chunk_size() -> None:
    """チャンクサイズを超える件数でもチャンク分割してupsertされること."""
    from app.repositories.monitoring.dividend_yield_monitoring_repository import _UPSERT_CHUNK_SIZE

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = None  # len(chunk) フォールバックを使用
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = DividendYieldMonitoringRepository(session=mock_session)

    records = [
        {
            "symbol": f"{i:04d}",
            "monitoring_date": date(2024, 1, 1),
        }
        for i in range(_UPSERT_CHUNK_SIZE + 1)
    ]

    result = await repo.bulk_upsert(records)

    # 2501件 → 2チャンクに分割、execute が2回呼ばれる
    assert mock_session.execute.call_count == 2
    assert result == _UPSERT_CHUNK_SIZE + 1
