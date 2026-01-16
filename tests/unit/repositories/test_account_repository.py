"""AccountRepository の単体テスト。

Repository の振る舞いを非同期セッションのモックで検証する。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account_repository import AccountRepository


class MockAccount:
    # テスト用ダミーとしてクラス属性に email を定義しておく（select 式評価対策）
    email = None

    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 0)
        self.email = kwargs.get("email")
        self.hashed_password = kwargs.get("hashed_password")
        self.full_name = kwargs.get("full_name")
        self.is_active = kwargs.get("is_active", True)
        self.last_login = kwargs.get("last_login")


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def repository(mock_session):
    repo = AccountRepository(mock_session)
    # テストでは実際の SQLAlchemy モデルを使わずモックに差し替える
    repo._model = MockAccount
    return repo


@pytest.mark.asyncio
async def test_get_by_email_found(repository, mock_session):
    expected = MockAccount(id=1, email="a@b.com")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected
    mock_session.execute = AsyncMock(return_value=mock_result)
    # SQLAlchemy の select() は SQLAlchemy マップ済みクラスを期待するため、
    # テストではモジュールレベルの select をダミーに差し替える
    import app.repositories.account_repository as ar

    original_select = ar.select

    class DummyStmt:
        def where(self, *a, **k):
            return self

    ar.select = lambda *a, **k: DummyStmt()
    try:
        res = await repository.get_by_email("a@b.com")
        assert res is expected
        mock_session.execute.assert_awaited_once()
    finally:
        ar.select = original_select


@pytest.mark.asyncio
async def test_create_account(repository, mock_session):
    mock_session.flush = AsyncMock()

    data = {"id": 2, "email": "x@y.com", "hashed_password": "h"}
    res = await repository.create_account(data)

    assert isinstance(res, MockAccount)
    assert res.email == "x@y.com"
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_last_login_found(repository, mock_session):
    existing = MockAccount(id=3)
    repository.get = AsyncMock(return_value=existing)
    mock_session.flush = AsyncMock()

    from datetime import datetime

    now = datetime.utcnow()
    res = await repository.update_last_login(3, now)
    assert res is existing
    assert existing.last_login == now
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_password_and_display_name(repository, mock_session):
    existing = MockAccount(id=4)
    repository.get = AsyncMock(return_value=existing)
    mock_session.flush = AsyncMock()

    res_pw = await repository.update_password(4, "newhash")
    assert res_pw is existing
    assert existing.hashed_password == "newhash"

    res_name = await repository.update_display_name(4, "New Name")
    assert res_name is existing
    assert existing.full_name == "New Name"


@pytest.mark.asyncio
async def test_deactivate_account(repository, mock_session):
    existing = MockAccount(id=5, is_active=True)
    repository.get = AsyncMock(return_value=existing)
    mock_session.flush = AsyncMock()

    res = await repository.deactivate_account(5)
    assert res is True
    assert existing.is_active is False


@pytest.mark.asyncio
async def test_deactivate_account_not_found(repository):
    repository.get = AsyncMock(return_value=None)
    res = await repository.deactivate_account(999)
    assert res is False
