"""StockCodeMapping Repository モジュール.

JPX 株式コード（stock_code）と EDINET 提出企業コード（sec_code）の対応関係を管理します。
"""

import logging
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.stock_master import StockCodeMapping
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)

_UPSERT_CHUNK_SIZE = 2500


class StockCodeMappingRepository(BaseRepository[StockCodeMapping]):
    """StockCodeMapping 用の Repository.

    Attributes:
        model: 対象の SQLAlchemy モデル（StockCodeMapping）
    """

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `StockCodeMapping` モデルをセットします."""
        super().__init__(session, model=StockCodeMapping)

    async def get_by_stock_code(self, stock_code: str) -> Optional[StockCodeMapping]:
        """JPX 株式コードで単一のレコードを取得する.

        Args:
            stock_code (str): JPX 株式コード

        Returns:
            Optional[StockCodeMapping]: 見つかればモデル、なければ None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.stock_code == stock_code)
        )
        return result.scalar_one_or_none()

    async def get_by_sec_code(self, sec_code: str) -> Optional[StockCodeMapping]:
        """EDINET 提出企業コードで単一のレコードを取得する.

        Args:
            sec_code (str): EDINET 提出企業コード

        Returns:
            Optional[StockCodeMapping]: 見つかればモデル、なければ None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.sec_code == sec_code)
        )
        return result.scalar_one_or_none()

    async def bulk_upsert(self, records: List[dict]) -> int:
        """複数レコードの一括 UPSERT を実行する.

        Args:
            records (List[dict]): UPSERT 対象のレコード辞書リスト

        Returns:
            int: 処理した件数

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        if not records:
            return 0

        table = self.model.__table__
        total = 0

        for i in range(0, len(records), _UPSERT_CHUNK_SIZE):
            chunk = records[i : i + _UPSERT_CHUNK_SIZE]
            insert_stmt = insert(table).values(chunk)

            # excluded は on_conflict_do_update 内で参照可能
            update_dict = {
                c.name: getattr(insert_stmt.excluded, c.name)
                for c in table.c
                if c.name not in ("id", "created_at")
            }

            stmt = insert_stmt.on_conflict_do_update(index_elements=["sec_code"], set_=update_dict)

            try:
                await self.session.execute(stmt)
                await self.session.flush()
                total += len(chunk)
            except SQLAlchemyError as e:
                logger.exception("bulk_upsert failed: %s", e)
                raise

        return total

    async def delete_all(self) -> int:
        """テーブル内の全レコードを削除する.

        Returns:
            int: 削除された件数

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        try:
            stmt = delete(self.model)
            result = await self.session.execute(stmt)
            await self.session.flush()
            # 型安全性のため、getattr でデフォルト 0 を使用する
            rc = getattr(result, "rowcount", 0)
            return int(rc or 0)
        except SQLAlchemyError as e:
            logger.exception("delete_all failed: %s", e)
            raise


__all__ = ["StockCodeMappingRepository"]
