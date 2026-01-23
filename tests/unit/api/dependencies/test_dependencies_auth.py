"""
単体テスト - Auth 依存性プロバイダ

app.api.dependencies.auth モジュールの単体テストを実施する。
JWTのデコード結果やアカウント取得結果に応じて適切な例外が発生するかを検証する。
"""

# AsyncMock not required here; remove unused import

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import auth as deps_auth


class DummyAccount:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.email = kwargs.get("email", "u@example.com")
        self.is_active = kwargs.get("is_active", True)
        self.is_superuser = kwargs.get("is_superuser", False)


@pytest.mark.asyncio
async def test_get_current_user_success(mock_db_session):
    token = "valid-token"
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    # モックデコードとリポジトリを差し替え
    payload = {"sub": "2"}

    def dummy_decode(t):
        return payload

    dummy_account = DummyAccount(id=2)

    class DummyRepo:
        def __init__(self, db):
            self.session = db

        async def get(self, _id):
            return dummy_account

    # patch
    deps_auth.auth_service.decode_access_token = dummy_decode
    deps_auth.AccountRepository = DummyRepo

    res = await deps_auth.get_current_user(
        credentials=creds, db=mock_db_session
    )
    assert res is dummy_account


@pytest.mark.asyncio
async def test_get_current_user_decode_failure(mock_db_session):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x")

    def raising_decode(t):
        raise ValueError("invalid")

    deps_auth.auth_service.decode_access_token = raising_decode

    with pytest.raises(HTTPException) as excinfo:
        await deps_auth.get_current_user(credentials=creds, db=mock_db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_missing_sub(mock_db_session):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x")

    def decode_no_sub(t):
        return {"foo": "bar"}

    deps_auth.auth_service.decode_access_token = decode_no_sub

    with pytest.raises(HTTPException) as excinfo:
        await deps_auth.get_current_user(credentials=creds, db=mock_db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_account_not_found(mock_db_session):
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="x")

    def decode_sub(t):
        return {"sub": "999"}

    class DummyRepoNone:
        def __init__(self, db):
            self.session = db

        async def get(self, _id):
            return None

    deps_auth.auth_service.decode_access_token = decode_sub
    deps_auth.AccountRepository = DummyRepoNone

    with pytest.raises(HTTPException) as excinfo:
        await deps_auth.get_current_user(credentials=creds, db=mock_db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_active_user_allows_active():
    account = DummyAccount(is_active=True)
    res = await deps_auth.get_current_active_user(current_user=account)
    assert res is account


@pytest.mark.asyncio
async def test_get_current_active_user_rejects_inactive():
    account = DummyAccount(is_active=False)
    with pytest.raises(HTTPException) as excinfo:
        await deps_auth.get_current_active_user(current_user=account)
    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_current_superuser_allows_superuser():
    account = DummyAccount(is_active=True, is_superuser=True)
    res = await deps_auth.get_current_superuser(current_user=account)
    assert res is account


@pytest.mark.asyncio
async def test_get_current_superuser_rejects_non_superuser():
    account = DummyAccount(is_active=True, is_superuser=False)
    with pytest.raises(HTTPException) as excinfo:
        await deps_auth.get_current_superuser(current_user=account)
    assert excinfo.value.status_code == status.HTTP_403_FORBIDDEN
