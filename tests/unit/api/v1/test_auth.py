"""Unit tests for app.api.v1.auth endpoints."""

from types import SimpleNamespace

import pytest

from app.api.v1 import auth as auth_module
from app.exceptions.business import (
    DuplicateEmailError,
    InvalidCredentialsError,
)


class DummyRepo:
    def __init__(self, existing=None):
        self._existing = existing
        self.updated_last_login = False

    async def get_by_email(self, email):
        return self._existing

    async def update_last_login(self, account_id, when):
        self.updated_last_login = True


@pytest.mark.asyncio
async def test_register_success(monkeypatch):
    payload = auth_module.AccountRegisterRequest(
        email="x@y.com", password="pass", display_name="X"
    )

    called = {}

    async def fake_register_user(repo, email, password, display_name):
        called["args"] = (email, password, display_name)
        return SimpleNamespace(id=1, email=email)

    monkeypatch.setattr(
        auth_module.auth_service, "register_user", fake_register_user
    )

    repo = DummyRepo(existing=None)
    res = await auth_module.register(payload=payload, repo=repo)

    assert getattr(res, "email") == "x@y.com"
    assert called["args"][0] == "x@y.com"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises():
    payload = auth_module.AccountRegisterRequest(
        email="a@b.com", password="pass", display_name="A"
    )

    repo = DummyRepo(existing=SimpleNamespace(id=1, email="a@b.com"))

    with pytest.raises(DuplicateEmailError):
        await auth_module.register(payload=payload, repo=repo)


@pytest.mark.asyncio
async def test_login_success_updates_last_login(monkeypatch):
    payload = auth_module.AccountLoginRequest(email="u@u.com", password="p")

    dummy_user = SimpleNamespace(id=2, email="u@u.com", hashed_password="h")

    async def fake_authenticate(repo, email, password):
        return dummy_user

    def fake_create_token(subject: str):
        return "tok"

    monkeypatch.setattr(
        auth_module.auth_service, "authenticate_user", fake_authenticate
    )
    monkeypatch.setattr(
        auth_module.auth_service, "create_access_token", fake_create_token
    )

    class R(DummyRepo):
        async def update_last_login(self, account_id, when):
            await super().update_last_login(account_id, when)

    repo = R()

    res = await auth_module.login(payload=payload, repo=repo)

    assert res["access_token"] == "tok"
    assert repo.updated_last_login is True


@pytest.mark.asyncio
async def test_login_invalid_credentials_raises(monkeypatch):
    payload = auth_module.AccountLoginRequest(email="u@u.com", password="p")

    async def fake_authenticate_none(repo, email, password):
        return None

    monkeypatch.setattr(
        auth_module.auth_service, "authenticate_user", fake_authenticate_none
    )

    repo = DummyRepo()

    with pytest.raises(InvalidCredentialsError):
        await auth_module.login(payload=payload, repo=repo)
