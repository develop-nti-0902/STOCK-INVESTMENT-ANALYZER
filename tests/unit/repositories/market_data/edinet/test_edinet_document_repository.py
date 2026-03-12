"""EdinetDocumentRepository の単体テスト集.

AsyncSession をモック化して DB に接続せずに振る舞いを検証します.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.edinet import EdinetDocument
from app.repositories.market_data.edinet.edinet_document_repository import EdinetDocumentRepository


@pytest.fixture
def mock_session():
    """AsyncSession のモックフィクスチャを返します."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    """EdinetDocumentRepository のインスタンスフィクスチャを返します."""
    return EdinetDocumentRepository(mock_session)


def make_model(**kwargs):
    """テスト用の EdinetDocument モデルインスタンスを作成します."""
    defaults = {
        "doc_id": "S1234567890",
        "sec_code": "0000012345",
        "submission_date": date(2024, 1, 1),
        "report_type": "annual",
    }
    defaults.update(kwargs)
    return EdinetDocument(**defaults)


@pytest.mark.asyncio
async def test_find_by_doc_id(repository, mock_session):
    """find_by_doc_id メソッドを検証します."""
    doc = make_model(id=1)

    # session.execute をモック
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=doc)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_by_doc_id("S1234567890")

    assert result == doc
    assert result.doc_id == "S1234567890"


@pytest.mark.asyncio
async def test_find_by_doc_id_not_found(repository, mock_session):
    """find_by_doc_id メソッド（見つからない場合）を検証します."""
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_by_doc_id("NOT_FOUND")

    assert result is None


@pytest.mark.asyncio
async def test_find_by_sec_code(repository, mock_session):
    """find_by_sec_code メソッドを検証します."""
    doc1 = make_model(id=1, sec_code="0000012345", submission_date=date(2024, 1, 1))
    doc2 = make_model(id=2, sec_code="0000012345", submission_date=date(2024, 3, 1))

    # session.execute をモック
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[doc2, doc1])
    mock_execute = AsyncMock()
    mock_execute.scalars = MagicMock(return_value=mock_scalars)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_by_sec_code("0000012345")

    assert len(result) == 2
    # 日付の新しい順（降順）
    assert result[0].submission_date == date(2024, 3, 1)
    assert result[1].submission_date == date(2024, 1, 1)


@pytest.mark.asyncio
async def test_find_by_sec_code_empty(repository, mock_session):
    """find_by_sec_code メソッド（見つからない場合）を検証します."""
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[])
    mock_execute = AsyncMock()
    mock_execute.scalars = MagicMock(return_value=mock_scalars)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_by_sec_code("NOTFOUND")

    assert result == []


@pytest.mark.asyncio
async def test_find_latest_by_sec_code(repository, mock_session):
    """find_latest_by_sec_code メソッドを検証します."""
    latest_doc = make_model(id=10, sec_code="0000012345", submission_date=date(2024, 6, 1))

    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=latest_doc)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_latest_by_sec_code("0000012345")

    assert result == latest_doc
    assert result.submission_date == date(2024, 6, 1)


@pytest.mark.asyncio
async def test_find_latest_by_sec_code_not_found(repository, mock_session):
    """find_latest_by_sec_code メソッド（見つからない場合）を検証します."""
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=None)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_latest_by_sec_code("NOTFOUND")

    assert result is None


@pytest.mark.asyncio
async def test_create_or_get_new_document(repository, mock_session):
    """create_or_get メソッド（新規作成）を検証します."""
    # mock_execute.first() がデータを返すようにセットアップ
    mock_row_mapping = {
        "id": 1,
        "doc_id": "S1234567890",
        "sec_code": "0000012345",
        "submission_date": "2024-01-01",
        "report_type": "annual",
    }
    mock_row = MagicMock()
    mock_row._mapping = mock_row_mapping

    mock_execute = AsyncMock()
    mock_execute.first = MagicMock(return_value=mock_row)
    mock_session.execute = AsyncMock(return_value=mock_execute)
    mock_session.flush = AsyncMock()

    result = await repository.create_or_get(
        doc_id="S1234567890",
        sec_code="0000012345",
        submission_date=date(2024, 1, 1),
        report_type="annual",
    )

    # create_or_get は upsert を呼び出して EdinetDocument を返す
    assert result is not None


@pytest.mark.asyncio
async def test_create_or_get_existing_document(repository, mock_session):
    """create_or_get メソッド（既存取得）を検証します."""
    existing_doc = make_model(id=1, doc_id="S1234567890")

    # existing の場合、最初の execute（find_by_doc_id）で見つける
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none = MagicMock(return_value=existing_doc)
    mock_session.execute.return_value = mock_execute

    result = await repository.create_or_get(
        doc_id="S1234567890",
        sec_code="0000012345",
        submission_date=date(2024, 1, 1),
        report_type="annual",
    )

    # 既存ドキュメントが返される
    assert result == existing_doc


@pytest.mark.asyncio
async def test_find_by_submission_date(repository, mock_session):
    """find_by_submission_date メソッドを検証します."""
    doc = make_model(id=1, submission_date=date(2024, 1, 1))

    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[doc])
    mock_execute = AsyncMock()
    mock_execute.scalars = MagicMock(return_value=mock_scalars)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_by_submission_date(date(2024, 1, 1))

    assert len(result) == 1
    assert result[0].submission_date == date(2024, 1, 1)


@pytest.mark.asyncio
async def test_find_by_date_range(repository, mock_session):
    """find_by_date_range メソッドを検証します."""
    doc1 = make_model(id=1, submission_date=date(2024, 1, 1))
    doc2 = make_model(id=2, submission_date=date(2024, 6, 1))

    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[doc1, doc2])
    mock_execute = AsyncMock()
    mock_execute.scalars = MagicMock(return_value=mock_scalars)
    mock_session.execute.return_value = mock_execute

    result = await repository.find_by_date_range(date(2024, 1, 1), date(2024, 6, 1))

    assert len(result) == 2


@pytest.mark.asyncio
async def test_count_by_sec_code(repository, mock_session):
    """count_by_sec_code メソッドを検証します."""
    mock_execute = MagicMock()
    mock_execute.scalar_one = MagicMock(return_value=5)
    mock_session.execute = AsyncMock(return_value=mock_execute)

    result = await repository.count_by_sec_code("0000012345")

    assert result == 5


@pytest.mark.asyncio
async def test_save_batch(repository, mock_session):
    """save_batch メソッドを検証します."""
    mock_row1 = MagicMock()
    mock_row1._mapping = {
        "id": 1,
        "doc_id": "S1234567890",
        "sec_code": "0000012345",
        "submission_date": "2024-01-01",
        "report_type": "annual",
    }
    mock_row2 = MagicMock()
    mock_row2._mapping = {
        "id": 2,
        "doc_id": "S0987654321",
        "sec_code": "0000054321",
        "submission_date": "2024-02-01",
        "report_type": "semi-annual",
    }

    mock_execute = AsyncMock()
    mock_execute.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
    mock_session.execute = AsyncMock(return_value=mock_execute)
    mock_session.flush = AsyncMock()

    data_list = [
        {
            "doc_id": "S1234567890",
            "sec_code": "0000012345",
            "submission_date": date(2024, 1, 1),
            "report_type": "annual",
        },
        {
            "doc_id": "S0987654321",
            "sec_code": "0000054321",
            "submission_date": date(2024, 2, 1),
            "report_type": "semi-annual",
        },
    ]

    result = await repository.save_batch(data_list)

    # save_batch は新規作成したモデルのリストを返す
    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_latest_by_sec_codes(repository, mock_session):
    """get_latest_by_sec_codes メソッドを検証します."""
    doc1 = make_model(id=1, sec_code="0000012345", submission_date=date(2024, 6, 1))
    doc2 = make_model(id=2, sec_code="0000054321", submission_date=date(2024, 5, 1))

    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=[doc1, doc2])
    mock_execute = AsyncMock()
    mock_execute.scalars = MagicMock(return_value=mock_scalars)
    mock_session.execute.return_value = mock_execute

    result = await repository.get_latest_by_sec_codes(["0000012345", "0000054321"])

    assert len(result) == 2
