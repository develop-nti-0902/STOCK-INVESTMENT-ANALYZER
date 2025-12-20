import logging
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_master import StockMaster
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def _escape_like(query: str, escape_char: str = "\\") -> str:
    """Escape SQL LIKE wildcards in `query` so they are treated literally.

    Replaces backslashes first, then '%' and '_' with escaped forms.
    Returns the escaped string (do not add surrounding '%' here).
    """
    if query is None:
        return ""
    # escape the escape char itself first
    esc = query.replace(escape_char, escape_char * 2)
    esc = esc.replace("%", escape_char + "%")
    esc = esc.replace("_", escape_char + "_")
    return esc


class StockMasterRepository(BaseRepository[StockMaster]):
    """
    StockMaster専用のRepository

    提供する主要メソッド:
    - get_by_symbol
    - get_by_market
    - search
    - bulk_upsert (PostgreSQLのON CONFLICTを利用)
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, model=StockMaster)

    async def get_by_symbol(self, symbol: str) -> Optional[StockMaster]:
        """銘柄コードで単一取得"""
        result = await self.session.execute(
            select(self.model).where(self.model.stock_code == symbol)
        )
        return result.scalar_one_or_none()

    async def get_all_active_symbols(self) -> List[str]:
        """アクティブな全銘柄コードを取得"""
        result = await self.session.execute(
            select(self.model.stock_code).where(self.model.is_active)
        )
        return [row[0] for row in result.all()]

    async def get_symbols_by_market(self, market: str) -> List[str]:
        """市場別銘柄コードを取得"""
        result = await self.session.execute(
            select(self.model.stock_code).where(
                self.model.market_category == market,
                self.model.is_active,
            )
        )
        return [row[0] for row in result.all()]

    async def get_symbols_by_sector(self, sector: str) -> List[str]:
        """業種別銘柄コードを取得"""
        result = await self.session.execute(
            select(self.model.stock_code).where(
                self.model.sector_name_33 == sector,
                self.model.is_active,
            )
        )
        return [row[0] for row in result.all()]

    async def get_by_market(self, market: str) -> List[StockMaster]:
        """市場区分で取得"""
        result = await self.session.execute(
            select(self.model).where(self.model.market_category == market)
        )
        return list(result.scalars().all())

    async def search(self, query: str) -> List[StockMaster]:
        """`stock_code` または `stock_name` に対する部分一致検索

        入力文字列に SQL LIKE ワイルドカード (`%`, `_`) を含んでいた場合、
        ユーザ入力をリテラルとして扱うためにそれらを自動的にエスケープします。
        ワイルドカードとして意図的に使いたい場合は、呼び出し元で明示的に
        エスケープ処理や直接 `select(...).where(...)` の使用を行ってください。
        """
        if not query:
            return []

        # ユーザー入力をエスケープしてリテラル検索にする
        escaped = _escape_like(query)
        like_expr = f"%{escaped}%"

        stmt = select(self.model).where(
            or_(
                self.model.stock_code.ilike(like_expr, escape="\\"),
                self.model.stock_name.ilike(like_expr, escape="\\"),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, records: List[dict]) -> List[StockMaster]:
        """一括作成はサポートしない。

        銘柄マスタは必ず一括 upsert による同期（`bulk_upsert`）で管理するため、
        単純な ORM ベースの `bulk_create` は誤用を防ぐため無効化します。
        """
        raise NotImplementedError(
            "bulk_create is not supported for StockMaster; "
            "use bulk_upsert instead"
        )

    async def upsert(self, data: dict) -> StockMaster:
        """単一UPSERTはサポートしない。

        本プロジェクトでは銘柄マスタに対しては一括更新のみを許可しているため、
        単一レコードの upsert は実行不可能とします。呼び出し側は `bulk_upsert`
        を利用してください。
        """
        raise NotImplementedError(
            "Single upsert is not supported for StockMaster; "
            "use bulk_upsert instead"
        )

    async def bulk_upsert(self, records: List[dict]) -> int:
        """既存のbulk_upsertも残す（入力件数を返す）"""
        if not records:
            return 0

        table = self.model.__table__
        insert_stmt = pg_insert(table).values(records)

        update_dict = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name != "id"
        }

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["stock_code"], set_=update_dict
        )

        try:
            await self.session.execute(stmt)
            await self.session.flush()
            await self.session.commit()
            return len(records)
        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.exception("bulk_upsert failed: %s", e)
            raise


__all__ = ["StockMasterRepository"]
