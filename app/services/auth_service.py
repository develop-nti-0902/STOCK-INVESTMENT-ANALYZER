from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from passlib.context import CryptContext

from app.repositories.account_repository import AccountRepository
from app.utils.config import get_settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    settings = get_settings()
    secret = getattr(settings, "SECRET_KEY", "secret")
    algorithm = getattr(settings, "ALGORITHM", "HS256")
    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=expire_minutes)
    )
    to_encode: Dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_access_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    secret = getattr(settings, "SECRET_KEY", "secret")
    algorithm = getattr(settings, "ALGORITHM", "HS256")
    payload = jwt.decode(token, secret, algorithms=[algorithm])
    return payload


async def authenticate_user(
    repo: AccountRepository, email: str, password: str
):
    user = await repo.get_by_email(email)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def register_user(
    repo: AccountRepository,
    email: str,
    password: str,
    display_name: Optional[str] = None,
):
    hashed = hash_password(password)
    data = {
        "email": email,
        "hashed_password": hashed,
        "full_name": display_name or email,
        "provider": "local",
        "is_active": True,
        "is_superuser": False,
    }
    return await repo.create_account(data)


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "authenticate_user",
    "register_user",
]
