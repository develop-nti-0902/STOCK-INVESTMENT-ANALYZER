"""Unit tests for accounts endpoints."""

from types import SimpleNamespace

import pytest

from app.api.v1 import accounts as accounts_module
from app.exceptions.business import (
    DuplicateEmailError,
    InvalidCredentialsError,
)


class DummyRepo:
    def __init__(self, email_exists=False):
        self._email_exists = email_exists
        self.updated = {}

    async def get_by_email(self, email):
        if self._email_exists:
            return SimpleNamespace(id=99, email=email)
        return None

    async def update(self, account_id, data):
        self.updated.update(data)
        return SimpleNamespace(
            id=account_id, email=data.get("email", "e@e.com")
        )

    async def update_display_name(self, account_id, display_name):
        self.updated["display_name"] = display_name
        return SimpleNamespace(id=account_id, full_name=display_name)

    async def update_password(self, account_id, hashed_password):
        self.updated["password"] = hashed_password

    async def deactivate_account(self, account_id):
        self.updated["deactivated"] = account_id


@pytest.mark.asyncio
async def test_me_returns_current_user():
    current = SimpleNamespace(id=1, email="a@b.com")
    res = await accounts_module.me(current_user=current)
    assert res is current


@pytest.mark.asyncio
async def test_update_me_email_and_display(monkeypatch):
    payload = accounts_module.AccountUpdateRequest(
        email="new@e.com", display_name="New"
    )

    repo = DummyRepo(email_exists=False)
    current_user = SimpleNamespace(id=5, email="old@e.com")

    res = await accounts_module.update_me(
        payload=payload, repo=repo, current_user=current_user
    )

    # email or display name updated -> return accordingly
    if getattr(res, "full_name", None) != "New":
        assert getattr(res, "email", None) == "new@e.com"


@pytest.mark.asyncio
async def test_update_me_duplicate_email_raises():
    payload = accounts_module.AccountUpdateRequest(email="dup@e.com")
    repo = DummyRepo(email_exists=True)
    current_user = SimpleNamespace(id=5, email="old@e.com")

    with pytest.raises(DuplicateEmailError):
        await accounts_module.update_me(
            payload=payload, repo=repo, current_user=current_user
        )


@pytest.mark.asyncio
async def test_change_password_success(monkeypatch):
    payload = accounts_module.PasswordChangeRequest(
        current_password="currpass", new_password="newpass"
    )

    def fake_verify(current, hashed):
        return True

    def fake_hash(new_pw):
        return "hashed" + new_pw

    monkeypatch.setattr(
        accounts_module.auth_service, "verify_password", fake_verify
    )
    monkeypatch.setattr(
        accounts_module.auth_service, "hash_password", fake_hash
    )

    repo = DummyRepo()
    current_user = SimpleNamespace(id=7, hashed_password="oldhash")

    res = await accounts_module.change_password(
        payload=payload, repo=repo, current_user=current_user
    )
    assert res is None
    assert repo.updated.get("password") == "hashednewpass"


@pytest.mark.asyncio
async def test_change_password_invalid_current(monkeypatch):
    payload = accounts_module.PasswordChangeRequest(
        current_password="bad", new_password="newpass"
    )

    def fake_verify_false(current, hashed):
        return False

    monkeypatch.setattr(
        accounts_module.auth_service, "verify_password", fake_verify_false
    )

    repo = DummyRepo()
    current_user = SimpleNamespace(id=7, hashed_password="oldhash")

    with pytest.raises(InvalidCredentialsError):
        await accounts_module.change_password(
            payload=payload, repo=repo, current_user=current_user
        )


@pytest.mark.asyncio
async def test_deactivate_me_calls_repo():
    repo = DummyRepo()
    current_user = SimpleNamespace(id=11)

    res = await accounts_module.deactivate_me(
        repo=repo, current_user=current_user
    )
    assert res is None
    assert repo.updated.get("deactivated") == 11
