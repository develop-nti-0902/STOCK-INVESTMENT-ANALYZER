"""`EdinetBalanceSheetRepository` の単体テスト集.

非同期セッションをモック化して DB に接続せずに振る舞いを検証します.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edinet_balance_sheet import EdinetBalanceSheet
from app.repositories.edinet_balance_sheet_repository import EdinetBalanceSheetRepository


@pytest.fixture
def mock_session():
    """AsyncSession のモックフィクスチャを返します."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    """`EdinetBalanceSheetRepository` のインスタンスフィクスチャを返します."""
    return EdinetBalanceSheetRepository(mock_session)


def make_model(**kwargs):
    """テスト用の `EdinetBalanceSheet` モデルインスタンスを作成します."""
    return EdinetBalanceSheet(**kwargs)


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
    }

    created = await repository.create(data)

    assert isinstance(created, EdinetBalanceSheet)
    assert created.sec_code == "7203"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()

    # find_by_period / find_by_doc_id / find_latest_by_sec_code の振る舞い
    expected = make_model(**data)

    # find_by_period -> 単一レコードを返すモック
    mock_result_period = MagicMock()
    mock_result_period.scalar_one_or_none.return_value = expected
    mock_session.execute = AsyncMock(return_value=mock_result_period)

    got = await repository.find_by_period("7203", date(2025, 3, 31))
    assert got is expected

    # find_by_doc_id -> 複数レコードを返す想定に変更
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [expected]
    mock_result_doc = MagicMock()
    mock_result_doc.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result_doc)

    got2 = await repository.find_by_doc_id("DOC1")
    assert got2 == [expected]

    # find_latest_by_sec_code -> 単一レコードを返すモックに戻す
    mock_result_latest = MagicMock()
    mock_result_latest.scalar_one_or_none.return_value = expected
    mock_session.execute = AsyncMock(return_value=mock_result_latest)

    got3 = await repository.find_latest_by_sec_code("7203")
    assert got3 is expected


@pytest.mark.asyncio
async def test_upsert_updates_when_newer_and_not_when_older(repository, mock_session):
    """upsert の新旧判定ロジックを検証します."""
    # シーケンス: upsert -> find_by_period の呼び出しが行われる

    # ケース1: 新しい submission_date の場合（更新される）
    input_data_new = {
        "doc_id": "DOC_NEW",
        "sec_code": "1001",
        "submission_date": date(2026, 1, 10),
        "period_end_date": date(2025, 12, 31),
    }
    new_model = make_model(**input_data_new)
    # session.execute の最初の呼び出し(upsert)は特に返り値を利用しないためダミーを返し、
    # 2回目(find_by_period)は期待モデルを返す
    mock_result_upsert = MagicMock()
    mock_result_find = MagicMock()
    mock_result_find.scalar_one_or_none.return_value = new_model
    mock_session.execute = AsyncMock(side_effect=[mock_result_upsert, mock_result_find])
    mock_session.flush = AsyncMock()

    ret = await repository.upsert(input_data_new)
    assert ret is new_model

    # ケース2: 古い submission_date の場合（更新されず既存のレコードが返る）
    input_data_old = {
        "doc_id": "DOC_OLD",
        "sec_code": "1001",
        "submission_date": date(2020, 1, 1),
        "period_end_date": date(2025, 12, 31),
    }
    existing_model = make_model(
        **{
            "doc_id": "DOC_EXIST",
            "sec_code": "1001",
            "submission_date": date(2025, 12, 31),
            "period_end_date": date(2025, 12, 31),
        }
    )
    # upsert の execute 呼び出し後に find_by_period が既存モデルを返す想定
    mock_result_upsert2 = MagicMock()
    mock_result_find2 = MagicMock()
    mock_result_find2.scalar_one_or_none.return_value = existing_model
    mock_session.execute = AsyncMock(side_effect=[mock_result_upsert2, mock_result_find2])
    mock_session.flush = AsyncMock()

    ret2 = await repository.upsert(input_data_old)
    assert ret2 is existing_model
    assert ret2.submission_date == date(2025, 12, 31)


@pytest.mark.asyncio
async def test_get_latest_by_sec_codes_and_count(repository, mock_session):
    """get_latest_by_sec_codes と count_by_sec_code の振る舞いを検証します."""
    # get_latest_by_sec_codes
    models = [
        make_model(
            doc_id="A",
            sec_code="1111",
            submission_date=date(2025, 1, 1),
            period_end_date=date(2024, 12, 31),
        ),
        make_model(
            doc_id="B",
            sec_code="2222",
            submission_date=date(2025, 2, 1),
            period_end_date=date(2024, 12, 31),
        ),
    ]

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = models
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    ret = await repository.get_latest_by_sec_codes(["1111", "2222"])
    assert ret == models

    # 空リストは空を返す
    ret_empty = await repository.get_latest_by_sec_codes([])
    assert ret_empty == []

    # count_by_sec_code
    mock_result_count = MagicMock()
    mock_result_count.scalar_one.return_value = 5
    mock_session.execute = AsyncMock(return_value=mock_result_count)
    cnt = await repository.count_by_sec_code("1111")
    assert cnt == 5
