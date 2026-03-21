"""Unit tests for `app.repositories.market_data.relative_strength.relative_strength_repository` model."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.relative_strength import RelativeStrength
from app.repositories.market_data.relative_strength import RelativeStrengthRepository


@pytest.mark.asyncio
async def test_relative_strength_repository_initialization():
    """RelativeStrengthRepository が正しく初期化されることを検証する."""
    mock_session = AsyncMock()
    repo = RelativeStrengthRepository(session=mock_session)

    assert repo.session == mock_session
    assert repo.model == RelativeStrength


@pytest.mark.asyncio
async def test_relative_strength_repository_bulk_upsert_success():
    """bulk_upsert が成功し、rowcount を返すことを検証する."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = RelativeStrengthRepository(session=mock_session)

    records = [
        {
            "symbol": "7203.T",
            "calculation_date": date(2024, 1, 10),
            "change_63days": Decimal("10.5"),
            "change_126days": Decimal("15.3"),
            "change_189days": Decimal("12.8"),
            "change_252days": Decimal("18.2"),
            "relative_strength_score": Decimal("14.20"),
        },
        {
            "symbol": "9984.T",
            "calculation_date": date(2024, 1, 10),
            "change_63days": Decimal("8.2"),
            "change_126days": Decimal("12.5"),
            "change_189days": Decimal("10.1"),
            "change_252days": Decimal("16.4"),
            "relative_strength_score": Decimal("11.80"),
        },
    ]

    result = await repo.bulk_upsert(records)

    assert result == 5
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_relative_strength_repository_bulk_upsert_empty_records():
    """bulk_upsert が空レコードリストで 0 を返すことを検証する."""
    mock_session = AsyncMock()
    repo = RelativeStrengthRepository(session=mock_session)

    result = await repo.bulk_upsert([])

    assert result == 0
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_relative_strength_repository_bulk_upsert_exception_handling():
    """bulk_upsert が例外をスローすることを検証する."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=Exception("Database error"))

    repo = RelativeStrengthRepository(session=mock_session)

    records = [
        {
            "symbol": "7203.T",
            "calculation_date": date(2024, 1, 10),
        }
    ]

    with pytest.raises(Exception) as exc_info:
        await repo.bulk_upsert(records)

    assert "Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_relative_strength_repository_delete_all():
    """delete_all が全件削除を実行し、rowcount を返すことを検証する."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 100
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = RelativeStrengthRepository(session=mock_session)

    result = await repo.delete_all()

    assert result == 100
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_relative_strength_repository_bulk_upsert_rowcount_fallback():
    """bulk_upsert が rowcount 属性がない場合、レコード数を返すことを検証する."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = RelativeStrengthRepository(session=mock_session)

    records = [
        {"symbol": "7203.T", "calculation_date": date(2024, 1, 10)},
        {"symbol": "9984.T", "calculation_date": date(2024, 1, 10)},
    ]

    result = await repo.bulk_upsert(records)

    assert result == 2  # レコード数が返される
