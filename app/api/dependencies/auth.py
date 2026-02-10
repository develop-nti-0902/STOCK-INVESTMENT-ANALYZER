"""Authentication dependency providers.

Provides FastAPI dependency callables to obtain the current user,
active user and superuser from a JWT access token.

Note: function docstrings use a single-line summary ending with a period.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounts import Account
from app.repositories.account_repository import AccountRepository
from app.services import auth_service
from app.utils.database import get_db

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Account:
    """JWT トークンから現在のユーザーを取得する依存性.

    - 正常: `Account` インスタンスを返す
    - トークンが無効またはユーザーが存在しない: HTTP 401 を発生させる
    """
    token = credentials.credentials
    try:
        payload = auth_service.decode_access_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"無効な認証トークンです: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンからユーザーIDを取得できませんでした",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = AccountRepository(db)
    account = await repo.get(int(user_id))
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return account


async def get_current_active_user(
    current_user: Account = Depends(get_current_user),
) -> Account:
    """アクティブなユーザーのみを許可する依存性.

    - `is_active` が False の場合は HTTP 403 を返す。
    """
    if not getattr(current_user, "is_active", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="アカウントが無効化されています",
        )
    return current_user


async def get_current_superuser(
    current_user: Account = Depends(get_current_active_user),
) -> Account:
    """スーパーユーザー権限をチェックする依存性.

    - `is_superuser` が False の場合は HTTP 403 を返す。
    """
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user


__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
]
