"""`EdinetProfitAndLossRepository` の単体テスト集.

非同期セッションをモック化して DB に接続せずに振る舞いを検証します.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.edinet import EdinetProfitAndLoss
from app.repositories.market_data.edinet.edinet_profit_and_loss_repository import (
    EdinetProfitAndLossRepository,
)


@pytest.fixture
def mock_session():
    """AsyncSession のモックフィクスチャを返します."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    """`EdinetProfitAndLossRepository` のインスタンスフィクスチャを返します."""
    return EdinetProfitAndLossRepository(mock_session)


def make_model(**kwargs):
    """テスト用の `EdinetProfitAndLoss` モデルインスタンスを作成します."""
    return EdinetProfitAndLoss(**kwargs)


@pytest.mark.asyncio
async def test_crud_basic_operations(repository, mock_session):
    """基本的な CRUD 処理の振る舞いを検証します."""
    # create は BaseRepository 側で flush を呼ぶだけなので、session.flush をモック
    mock_session.flush = AsyncMock()

    data = {
        "doc_id": "DOC1",
        "sec_code": "7203",
        "submission_date": date(2025, 12, 31),
        "period_end_date": date(2025, 3, 31),
        "fiscal_year": 2024,
        "operating_income": 1500.0,
        "eps": 120.5,
    }

    created = await repository.create(data)

    assert isinstance(created, EdinetProfitAndLoss)
    assert created.sec_code == "7203"
    assert created.operating_income == 1500.0
    assert created.eps == 120.5
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_find_latest_by_sec_code(repository, mock_session):
    """`find_latest_by_sec_code` の振る舞いを検証します."""
    # Mock result with scalar_one_or_none method
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = make_model(
        sec_code="7203",
        period_end_date=date(2025, 3, 31),
        operating_income=1500.0,
        eps=120.5,
    )

    mock_session.execute.return_value = mock_result

    result = await repository.find_latest_by_sec_code("7203")

    assert result is not None
    assert result.sec_code == "7203"
    assert result.operating_income == 1500.0
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_by_period(repository, mock_session):
    """`find_by_period` の振る舞いを検証します."""
    # Mock result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = make_model(
        sec_code="7203",
        period_end_date=date(2025, 3, 31),
        eps=120.5,
    )

    mock_session.execute.return_value = mock_result

    result = await repository.find_by_period("7203", date(2025, 3, 31))

    assert result is not None
    assert result.sec_code == "7203"
    assert result.eps == 120.5
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_find_by_doc_id(repository, mock_session):
    """`find_by_doc_id` の振る舞いを検証します."""
    # Mock result with scalars().all()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [
        make_model(doc_id="DOC1", sec_code="7203", operating_income=1500.0),
        make_model(doc_id="DOC1", sec_code="7203", operating_income=1400.0),
    ]
    mock_result.scalars.return_value = mock_scalars

    mock_session.execute.return_value = mock_result

    result = await repository.find_by_doc_id("DOC1")

    assert len(result) == 2
    assert all(r.doc_id == "DOC1" for r in result)
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_success(repository, mock_session):
    """`upsert` の成功ケースを検証します."""
    # Setup mocks for upsert with RETURNING clause
    mock_session.flush = AsyncMock()

    # Mock the result object that includes first() for RETURNING clause
    mock_row = MagicMock()
    mock_row._mapping = {
        "sec_code": "7203",
        "period_end_date": date(2025, 3, 31),
        "operating_income": 1500.0,
        "eps": 120.5,
    }

    mock_result = MagicMock()
    mock_result.first.return_value = mock_row

    mock_session.execute = AsyncMock(return_value=mock_result)

    data = {
        "sec_code": "7203",
        "period_end_date": date(2025, 3, 31),
        "operating_income": 1500.0,
        "eps": 120.5,
    }

    result = await repository.upsert(data)

    assert result is not None
    assert result.sec_code == "7203"
    assert result.operating_income == 1500.0
    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_empty_data_raises_error(repository):
    """`upsert` で空データの場合にエラーが発生することを検証します."""
    with pytest.raises(ValueError, match="data is required for upsert"):
        await repository.upsert({})


@pytest.mark.asyncio
async def test_get_latest_by_sec_codes(repository, mock_session):
    """`get_latest_by_sec_codes` の振る舞いを検証します."""
    # Mock result
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [
        make_model(sec_code="7203", period_end_date=date(2025, 3, 31)),
        make_model(sec_code="9984", period_end_date=date(2025, 2, 28)),
    ]
    mock_result.scalars.return_value = mock_scalars

    mock_session.execute.return_value = mock_result

    result = await repository.get_latest_by_sec_codes(["7203", "9984"])

    assert len(result) == 2
    assert result[0].sec_code == "7203"
    assert result[1].sec_code == "9984"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_latest_by_sec_codes_empty_list(repository):
    """`get_latest_by_sec_codes` で空リストの場合の振る舞いを検証します."""
    result = await repository.get_latest_by_sec_codes([])
    assert result == []


@pytest.mark.asyncio
async def test_count_by_sec_code(repository, mock_session):
    """`count_by_sec_code` の振る舞いを検証します."""
    # Mock result
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 3

    mock_session.execute.return_value = mock_result

    result = await repository.count_by_sec_code("7203")

    assert result == 3
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_save_batch_upsert_success(repository, mock_session):
    """`save_batch_upsert` の成功ケースを検証します."""
    # Setup mocks for save_batch with RETURNING clause
    mock_session.flush = AsyncMock()

    # Mock the result object that includes fetchall() for RETURNING clause
    mock_rows = [
        MagicMock(
            _mapping={
                "sec_code": "7203",
                "period_end_date": date(2025, 3, 31),
                "operating_income": 1500.0,
                "eps": 120.5,
            }
        ),
        MagicMock(
            _mapping={
                "sec_code": "9984",
                "period_end_date": date(2025, 2, 28),
                "operating_income": 1400.0,
                "eps": 110.5,
            }
        ),
    ]

    mock_result = MagicMock()
    mock_result.fetchall.return_value = mock_rows

    mock_session.execute = AsyncMock(return_value=mock_result)

    data_list = [
        {
            "sec_code": "7203",
            "period_end_date": date(2025, 3, 31),
            "operating_income": 1500.0,
            "eps": 120.5,
        },
        {
            "sec_code": "9984",
            "period_end_date": date(2025, 2, 28),
            "operating_income": 1400.0,
            "eps": 110.5,
        },
    ]

    result = await repository.save_batch(data_list)

    assert len(result) == 2
    assert result[0].sec_code == "7203"
    assert result[1].sec_code == "9984"
    mock_session.execute.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_save_batch_upsert_empty_list(repository):
    """`save_batch_upsert` で空リストの場合の振る舞いを検証します."""
    result = await repository.save_batch([])
    assert result == []


@pytest.mark.asyncio
async def test_save_batch_upsert_none_raises_error(repository):
    """`save_batch_upsert` で None の場合にエラーが発生することを検証します."""
    with pytest.raises(ValueError, match="data_list is required for save_batch_upsert"):
        await repository.save_batch(None)
