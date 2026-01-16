from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccountRegisterRequest(BaseModel):
    """アカウント登録リクエスト"""

    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(
        ...,
        min_length=4,
        max_length=128,
        description="パスワード（4文字以上）",
    )
    display_name: str = Field(
        ..., min_length=1, max_length=100, description="表示名"
    )

    # パスワードの強度要件を緩和（4文字以上を必須とし、数字/文字の混在は不要）


class AccountLoginRequest(BaseModel):
    """アカウントログインリクエスト"""

    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., description="パスワード")


class AccountUpdateRequest(BaseModel):
    """アカウント情報更新リクエスト"""

    display_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="表示名"
    )
    email: Optional[EmailStr] = Field(None, description="メールアドレス")


class PasswordChangeRequest(BaseModel):
    """パスワード変更リクエスト"""

    current_password: str = Field(..., description="現在のパスワード")
    new_password: str = Field(
        ...,
        min_length=4,
        max_length=128,
        description="新しいパスワード（4文字以上）",
    )

    # パスワード強度バリデータは不要（4文字以上を許容、数字のみ/文字のみ可）


class AccountResponse(BaseModel):
    """アカウント情報レスポンス"""

    id: int
    email: str
    full_name: Optional[str] = Field(None, serialization_alias="display_name")
    is_active: bool
    is_superuser: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TokenResponse(BaseModel):
    """トークンレスポンス"""

    access_token: str = Field(..., description="アクセストークン")
    token_type: str = Field(default="bearer", description="トークンタイプ")
