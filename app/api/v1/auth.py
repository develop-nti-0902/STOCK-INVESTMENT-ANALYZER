"""認証関連API. 登録・ログインなどのエンドポイントを提供します."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status

from app.exceptions.business import DuplicateEmailError, InvalidCredentialsError
from app.repositories.account_repository import AccountRepository
from app.schemas.accounts import (
    AccountLoginRequest,
    AccountRegisterRequest,
    AccountResponse,
    TokenResponse,
)
from app.services.auth import auth_service
from app.utils.database import get_db

router = APIRouter(tags=["user"])  # OpenAPI tag: user


async def get_account_repo(db=Depends(get_db)) -> AccountRepository:
    return AccountRepository(db)


@router.post(
    "/register",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: AccountRegisterRequest,
    repo: AccountRepository = Depends(get_account_repo),
):
    existing = await repo.get_by_email(payload.email)
    if existing is not None:
        raise DuplicateEmailError()

    user = await auth_service.register_user(
        repo, payload.email, payload.password, payload.display_name
    )
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: AccountLoginRequest,
    repo: AccountRepository = Depends(get_account_repo),
):
    user = await auth_service.authenticate_user(repo, payload.email, payload.password)
    if user is None:
        raise InvalidCredentialsError()

    token = auth_service.create_access_token(subject=str(getattr(user, "id", payload.email)))
    # 更新は非ブロッキング（DB上で記録）
    try:
        user_id = getattr(user, "id", None)
        if user_id is not None:
            await repo.update_last_login(int(user_id), datetime.now(timezone.utc))
    except Exception:
        # ログのために黙殺し、トークン発行自体は成功扱いとする
        pass

    return {"access_token": token, "token_type": "bearer"}


__all__ = ["router"]
