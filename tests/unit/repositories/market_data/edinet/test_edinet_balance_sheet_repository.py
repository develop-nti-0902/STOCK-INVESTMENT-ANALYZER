"""Unit tests (minimal) for Edinet balance sheet repository."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.market_data.edinet.edinet_balance_sheet_repository import (
    EdinetBalanceSheetRepository,
)


def test_import_edinet_balance_sheet_repository():
    """Smoke test: import repository module."""
    import app.repositories.market_data.edinet.edinet_balance_sheet_repository as m

    assert m is not None


@pytest.mark.asyncio
async def test_save_batch_exceeds_chunk_size():
    """チャンクサイズを超える件数でもチャンク分割してsave_batchされること."""
    from app.repositories.market_data.edinet.edinet_balance_sheet_repository import (
        _UPSERT_CHUNK_SIZE,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []  # 行データなし（チャンク分割の検証のみ）
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    repo = EdinetBalanceSheetRepository(session=mock_session)

    data_list = [
        {
            "edinet_document_id": i + 1,
            "period_end_date": date(2024, 3, 31),
        }
        for i in range(_UPSERT_CHUNK_SIZE + 1)
    ]

    results = await repo.save_batch(data_list)

    # 2501件 → 2チャンクに分割、execute が2回呼ばれる
    assert mock_session.execute.call_count == 2
    # flush はループ後に1回
    assert mock_session.flush.call_count == 1
    assert results == []
