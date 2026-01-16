import types
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.v1 import auth as auth_module
from app.main import app as fastapi_app


@pytest.mark.asyncio
async def test_register_success(client, mock_db_session):
    mock_repo = AsyncMock()
    mock_repo.get_by_email.return_value = None

    created = types.SimpleNamespace(
        id=1,
        email="user@example.com",
        display_name="User",
        is_active=True,
        is_superuser=False,
        last_login=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_repo.create_account.return_value = created

    fastapi_app.dependency_overrides[auth_module.get_account_repo] = (
        lambda: mock_repo
    )

    payload = {
        "email": "user@example.com",
        "password": "pass1234",
        "display_name": "User",
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    # cleanup
    fastapi_app.dependency_overrides.pop(auth_module.get_account_repo, None)

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == payload["email"]


@pytest.mark.asyncio
async def test_register_duplicate(client, mock_db_session):
    mock_repo = AsyncMock()
    existing = types.SimpleNamespace(id=2, email="dup@example.com")
    mock_repo.get_by_email.return_value = existing

    fastapi_app.dependency_overrides[auth_module.get_account_repo] = (
        lambda: mock_repo
    )

    payload = {
        "email": "dup@example.com",
        "password": "pass",
        "display_name": "Dup",
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    fastapi_app.dependency_overrides.pop(auth_module.get_account_repo, None)

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client, mock_db_session):
    mock_repo = AsyncMock()
    user = types.SimpleNamespace(id=3, email="login@example.com")

    # override authenticate_user to avoid password hashing concerns
    original_authenticate = auth_module.auth_service.authenticate_user
    auth_module.auth_service.authenticate_user = AsyncMock(return_value=user)
    mock_repo.update_last_login = AsyncMock(return_value=user)

    fastapi_app.dependency_overrides[auth_module.get_account_repo] = (
        lambda: mock_repo
    )

    payload = {"email": "login@example.com", "password": "any"}
    resp = client.post("/api/v1/auth/login", json=payload)

    # cleanup
    fastapi_app.dependency_overrides.pop(auth_module.get_account_repo, None)
    auth_module.auth_service.authenticate_user = original_authenticate

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
