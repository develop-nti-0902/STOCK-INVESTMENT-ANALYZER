"""`ScreeningResultRepository` の単体テスト."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.validation import FieldValidationError
from app.models.screening import ScreeningResult
from app.repositories.screening.screening_result_repository import ScreeningResultRepository


@pytest.fixture
def mock_session():
    """AsyncSession のモックフィクスチャを返します."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    """ScreeningResultRepository のインスタンスフィクスチャを返します."""
    return ScreeningResultRepository(mock_session)


def make_model(**kwargs):
    """テスト用の ScreeningResult モデルインスタンスを作成します."""
    defaults = {
        "symbol": "7203",
        "evaluation_date": date(2026, 2, 19),
        "pass_required_conditions": True,
        "status": "priority",
    }
    defaults.update(kwargs)
    return ScreeningResult(**defaults)


@pytest.mark.asyncio
async def test_upsert_inserts_and_returns_model(repository, mock_session):
    """upsert が挿入/更新を呼び出し、最新レコードを返すことを確認します."""
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    expected = make_model(total_score=92)
    repository.find_latest_by_symbol = AsyncMock(return_value=expected)

    data = {
        "symbol": "7203",
        "evaluation_date": date(2026, 2, 19),
        "pass_required_conditions": True,
        "status": "priority",
        "total_score": 92,
    }

    result = await repository.upsert(data)

    assert result is expected
    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()
    repository.find_latest_by_symbol.assert_awaited_once_with("7203")


@pytest.mark.asyncio
async def test_upsert_empty_data_raises_error(repository):
    """空の辞書を渡した場合に ValueError が発生することを確認します."""
    with pytest.raises(ValueError, match="data is required for upsert"):
        await repository.upsert({})


@pytest.mark.asyncio
async def test_find_latest_by_symbol(repository, mock_session):
    """最新レコードを返すクエリを実行することを確認します."""
    mock_result = MagicMock()
    expected = make_model()
    mock_result.scalar_one_or_none.return_value = expected
    mock_session.execute.return_value = mock_result

    result = await repository.find_latest_by_symbol("7203")

    assert result is expected
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_by_symbol_returns_history(repository, mock_session):
    """特定銘柄の履歴をリストで返すことを確認します."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    records = [
        make_model(evaluation_date=date(2026, 2, 19)),
        make_model(evaluation_date=date(2025, 2, 19)),
    ]
    mock_scalars.all.return_value = records
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    result = await repository.find_by_symbol("7203")

    assert result == records
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_filters_and_pagination(repository, mock_session):
    """フィルターを適用したページング取得が動くことを確認します."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    record = make_model(symbol="6758", total_score=88)
    mock_scalars.all.return_value = [record]
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    result = await repository.list(skip=1, limit=5, min_score=70, status="active", symbols=["6758"])

    assert result == [record]
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_invalid_pagination_raises(repository):
    """マイナスの skip を与えると FieldValidationError が発生することを確認します."""
    with pytest.raises(FieldValidationError):
        await repository.list(skip=-1, limit=10)
