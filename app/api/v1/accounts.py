from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_current_active_user
from app.exceptions.business import (
    DuplicateEmailError,
    InvalidCredentialsError,
)
from app.repositories.account_repository import AccountRepository
from app.schemas.accounts import (
    AccountResponse,
    AccountUpdateRequest,
    PasswordChangeRequest,
)
from app.services import auth_service
from app.utils.database import get_db

router = APIRouter(tags=["user"])  # OpenAPI tag: user


async def get_account_repo(db=Depends(get_db)) -> AccountRepository:
    return AccountRepository(db)


@router.get("/me", response_model=AccountResponse)
async def me(current_user=Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=AccountResponse)
async def update_me(
    payload: AccountUpdateRequest,
    repo: AccountRepository = Depends(get_account_repo),
    current_user=Depends(get_current_active_user),
):
    updated = current_user

    # Email update: check duplication
    if payload.email and payload.email != getattr(current_user, "email", None):
        existing = await repo.get_by_email(payload.email)
        if existing is not None:
            raise DuplicateEmailError()
        updated = await repo.update(current_user.id, {"email": payload.email})

    # Display name update
    if payload.display_name is not None:
        updated = await repo.update_display_name(
            current_user.id, payload.display_name
        )

    return updated


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    repo: AccountRepository = Depends(get_account_repo),
    current_user=Depends(get_current_active_user),
):
    ok = auth_service.verify_password(
        payload.current_password, getattr(current_user, "hashed_password", "")
    )
    if not ok:
        raise InvalidCredentialsError()

    new_hashed = auth_service.hash_password(payload.new_password)
    await repo.update_password(current_user.id, new_hashed)
    return None


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_me(
    repo: AccountRepository = Depends(get_account_repo),
    current_user=Depends(get_current_active_user),
):
    await repo.deactivate_account(current_user.id)
    return None


__all__ = ["router"]
