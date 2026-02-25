"""Account リポジトリ実装.

`Account` モデルに対する CRUD 操作やユーティリティ的な更新処理を提供します。
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.repositories.core.base import BaseRepository
from app.utils.database import flush_return_with_log

logger = logging.getLogger(__name__)


class AccountRepository(BaseRepository[Account]):
    """アカウント操作用の Repository 実装."""

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `Account` モデルをセットします."""
        super().__init__(session, model=Account)

    async def get_by_email(self, email: str) -> Optional[Account]:
        """メールアドレスでアカウントを取得する."""
        result = await self.session.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()

    async def create_account(self, data: Dict[str, Any]) -> Account:
        """アカウントを作成して作成済みインスタンスを返す."""
        return await self.create(data)

    async def update_last_login(
        self, account_id: int, last_login: Optional[datetime]
    ) -> Optional[Account]:
        """最終ログイン時刻を更新して更新後のインスタンスを返す."""
        instance = await self.get(account_id)
        if instance is None:
            return None
        instance.last_login = last_login
        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush updated last_login for id=%s",
            account_id,
        )

    async def update_password(self, account_id: int, hashed_password: str) -> Optional[Account]:
        """パスワードハッシュを更新する."""
        instance = await self.get(account_id)
        if instance is None:
            return None
        instance.hashed_password = hashed_password
        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush updated password for id=%s",
            account_id,
        )

    async def update_display_name(
        self, account_id: int, display_name: Optional[str]
    ) -> Optional[Account]:
        """表示名を更新する."""
        instance = await self.get(account_id)
        if instance is None:
            return None
        instance.full_name = display_name
        return await flush_return_with_log(
            self.session,
            instance,
            logger,
            "Failed to flush updated display name for id=%s",
            account_id,
        )

    async def deactivate_account(self, account_id: int) -> bool:
        """アカウントを無効化する。存在しなければ False を返す."""
        instance = await self.get(account_id)
        if instance is None:
            return False
        instance.is_active = False
        try:
            await flush_return_with_log(
                self.session,
                True,
                logger,
                "Failed to flush deactivate account id=%s",
                account_id,
            )
            return True
        except SQLAlchemyError:
            logger.exception("Failed to deactivate account id=%s", account_id)
            raise


__all__ = ["AccountRepository"]
