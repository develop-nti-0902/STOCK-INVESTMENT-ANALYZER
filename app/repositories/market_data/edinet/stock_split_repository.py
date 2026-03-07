"""`StockSplit` 用リポジトリ実装.

基本的な CRUD と検索・簡易 upsert を提供します。
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.edinet.stock_split import StockSplit
from app.repositories.core.base import BaseRepository


class StockSplitRepository(BaseRepository[StockSplit]):
    """`stock_split` テーブルの CRUD を扱うリポジトリ."""

    def __init__(self, session: AsyncSession):
        """初期化処理で AsyncSession とモデルクラスをセットします."""
        super().__init__(session, model=StockSplit)

    async def find_by_code(self, code: str) -> List[StockSplit]:
        """銘柄コードから株式分割レコードを検索します."""
        if not code:
            return []
        result = await self.session.execute(select(self.model).where(self.model.code == code))
        return list(result.scalars().all())

    async def find_by_date(self, code: str, effective_date: date) -> Optional[StockSplit]:
        """銘柄コードと発効日から株式分割レコードを検索します."""
        result = await self.session.execute(
            select(self.model).where(
                self.model.code == code, self.model.effective_date == effective_date
            )
        )
        return result.scalar_one_or_none()

    async def upsert(self, data: dict) -> StockSplit:
        """簡易的な upsert 実装: code+effective_date で既存を検索し、あれば更新、なければ作成する."""
        if not data:
            raise ValueError("data is required for upsert")

        code = data.get("code")
        effective_date = data.get("effective_date")
        if code is None or effective_date is None:
            raise ValueError("code and effective_date are required for upsert")

        existing = await self.find_by_date(code, effective_date)
        if existing is None:
            return await self.create(data)

        # update existing fields
        for k, v in data.items():
            if hasattr(existing, k) and k not in ("id", "created_at"):
                setattr(existing, k, v)

        return await self._add_and_flush(existing)


__all__ = ["StockSplitRepository"]
