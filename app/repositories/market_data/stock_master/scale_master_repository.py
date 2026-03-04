"""規模マスター Repository モジュール."""

from typing import Optional, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.stock_master import ScaleMaster
from app.repositories.core.base import BaseRepository


class ScaleMasterRepository(BaseRepository[ScaleMaster]):
    """規模マスター用 Repository."""

    def __init__(self, session: AsyncSession):
        """初期化."""
        super().__init__(session, model=ScaleMaster)

    async def get_by_code(self, code: str) -> Optional[ScaleMaster]:
        """コードで単一レコード取得.

        Args:
            code (str): 規模コード

        Returns:
            Optional[ScaleMaster]: 見つかればモデル、なければ None
        """
        result = await self.session.execute(select(self.model).where(self.model.code == code))
        return result.scalar_one_or_none()

    async def get_or_create(self, code: str, name: str) -> tuple[ScaleMaster, bool]:
        """Upsert: 存在する場合は取得、ない場合は作成.

        Args:
            code (str): 規模コード
            name (str): 規模区分名

        Returns:
            tuple[ScaleMaster, bool]: (レコード, 新規作成フラグ)
        """
        existing = await self.get_by_code(code)
        if existing:
            return existing, False

        new_record = self.model(code=code, name=name)
        self.session.add(new_record)
        await self.session.flush()
        return new_record, True

    async def list_all(self) -> list[ScaleMaster]:
        """全レコード取得.

        Returns:
            list[ScaleMaster]: 全レコードのリスト
        """
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def delete_all(self) -> int:
        """全レコード削除.

        Returns:
            int: 削除したレコード数
        """
        from sqlalchemy import delete

        stmt = delete(self.model)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount) if result.rowcount else 0  # type: ignore[attr-defined]


__all__ = ["ScaleMasterRepository"]
