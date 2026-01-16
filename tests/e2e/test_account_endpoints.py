import types
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.api.dependencies import auth as auth_deps
from app.main import app as fastapi_app
from app.services import auth_service


@pytest.mark.asyncio
async def test_get_me(client, mock_db_session):
    user = types.SimpleNamespace(
        id=10,
        email="me@example.com",
        display_name="Me",
        is_active=True,
        is_superuser=False,
        last_login=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    fastapi_app.dependency_overrides[auth_deps.get_current_active_user] = (
        lambda: user
    )

    resp = client.get("/api/v1/accounts/me")
    fastapi_app.dependency_overrides.pop(
        auth_deps.get_current_active_user, None
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_update_me_display_name(client, mock_db_session):
    user = types.SimpleNamespace(
        id=11,
        email="u@example.com",
        display_name="Old",
        hashed_password="hash",
        is_active=True,
        is_superuser=False,
        last_login=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    fastapi_app.dependency_overrides[auth_deps.get_current_active_user] = (
        lambda: user
    )

    # mock AccountRepository used by endpoint
    mock_repo = AsyncMock()
    mock_repo.get_by_email.return_value = None
    mock_repo.update_display_name.return_value = types.SimpleNamespace(
        **{**user.__dict__, **{"display_name": "New"}}
    )

    from app.api.v1 import accounts as accounts_module

    fastapi_app.dependency_overrides[accounts_module.get_account_repo] = (
        lambda: mock_repo
    )

    payload = {"display_name": "New"}
    resp = client.put("/api/v1/accounts/me", json=payload)

    # cleanup
    fastapi_app.dependency_overrides.pop(
        auth_deps.get_current_active_user, None
    )
    fastapi_app.dependency_overrides.pop(
        accounts_module.get_account_repo, None
    )

    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New"


@pytest.mark.asyncio
async def test_change_password_success(client, mock_db_session):
    user = types.SimpleNamespace(
        id=12,
        email="pw@example.com",
        display_name="Pw",
        hashed_password=auth_service.hash_password("old"),
        is_active=True,
        is_superuser=False,
        last_login=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    fastapi_app.dependency_overrides[auth_deps.get_current_active_user] = (
        lambda: user
    )

    mock_repo = AsyncMock()
    mock_repo.update_password.return_value = user

    from app.api.v1 import accounts as accounts_module

    fastapi_app.dependency_overrides[accounts_module.get_account_repo] = (
        lambda: mock_repo
    )

    payload = {"current_password": "old", "new_password": "newpass"}
    resp = client.put("/api/v1/accounts/me/password", json=payload)

    fastapi_app.dependency_overrides.pop(
        auth_deps.get_current_active_user, None
    )
    fastapi_app.dependency_overrides.pop(
        accounts_module.get_account_repo, None
    )

    assert resp.status_code == 204
