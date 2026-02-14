"""Stock master Repository モジュール.

銘柄マスター（StockMaster）に対する参照、検索、一括更新処理を提供します。
部分一致検索や PostgreSQL の UPSERT（ON CONFLICT）を用いた一括更新を扱います。
"""

import logging
from typing import Any, List, Optional

from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.stock_master import IS_ACTIVE, StockMaster
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def _escape_like(query: str, escape_char: str = "\\") -> str:
    r"""LIKE クエリ用のエスケープを行う.

    Args:
        query (str): 入力クエリ文字列
        escape_char (str): エスケープ文字（デフォルト '\\'）

    Returns:
        str: エスケープ済みクエリ（周囲のワイルドカード '%' は付与しない）
    """
    if query is None:
        return ""
    # エスケープ文字自体を先にエスケープする
    esc = query.replace(escape_char, escape_char * 2)
    esc = esc.replace("%", escape_char + "%")
    esc = esc.replace("_", escape_char + "_")
    return esc


class StockMasterRepository(BaseRepository[StockMaster]):
    """銘柄マスター用の Repository.

    Attributes:
        model: 対象の SQLAlchemy モデル（StockMaster）
    """

    def __init__(self, session: AsyncSession):
        """初期化。セッションを受け取り `StockMaster` モデルをセットします."""
        super().__init__(session, model=StockMaster)

    async def get_by_symbol(self, symbol: str) -> Optional[StockMaster]:
        """銘柄コードで単一のレコードを取得する.

        Args:
            symbol (str): 銘柄コード

        Returns:
            Optional[StockMaster]: 見つかればモデル、なければ None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.stock_code == symbol)
        )
        return result.scalar_one_or_none()

    async def get_all_active_symbols(self) -> List[str]:
        """有効（active）な全銘柄コードを取得する.

        Returns:
            List[str]: 銘柄コードのリスト
        """
        result = await self.session.execute(
            select(self.model.stock_code).where(self.model.is_active == IS_ACTIVE)
        )
        return [row[0] for row in result.all()]

    async def get_symbols_by_market(self, market: str) -> List[str]:
        """指定市場の銘柄コードを取得する.

        Args:
            market (str): 市場名

        Returns:
            List[str]: 銘柄コードリスト
        """
        result = await self.session.execute(
            select(self.model.stock_code).where(
                self.model.market_category == market,
                self.model.is_active == IS_ACTIVE,
            )
        )
        return [row[0] for row in result.all()]

    async def get_symbols_by_sector(self, sector: str) -> List[str]:
        """業種別の銘柄コードを取得する.

        Args:
            sector (str): 業種名

        Returns:
            List[str]: 銘柄コードリスト
        """
        result = await self.session.execute(
            select(self.model.stock_code).where(
                self.model.sector_name_33 == sector,
                self.model.is_active == IS_ACTIVE,
            )
        )
        return [row[0] for row in result.all()]

    async def get_by_market(self, market: str) -> List[StockMaster]:
        """市場区分でレコードを取得する.

        Args:
            market (str): 市場名

        Returns:
            List[StockMaster]: モデルリスト
        """
        result = await self.session.execute(
            select(self.model).where(self.model.market_category == market)
        )
        return list(result.scalars().all())

    async def search(self, query: str) -> List[StockMaster]:
        """部分一致で `stock_code` または `stock_name` を検索する.

        ユーザ入力にワイルドカード文字が含まれる場合、自動的にエスケープして
        リテラル検索を行います。ワイルドカードを意図的に利用する場合は、
        呼び出し側で明示的にクエリを構築してください。

        Args:
            query (str): 検索クエリ文字列

        Returns:
            List[StockMaster]: 検索結果のモデルリスト
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
        """一括作成はサポートしない.

        Notes:
            銘柄マスタは `bulk_upsert` による同期を前提としているため、
            単純な `bulk_create` は意図しない状態を招くため無効化します。

        Raises:
            NotImplementedError: 常に発生
        """
        raise NotImplementedError(
            "bulk_create is not supported for StockMaster; use bulk_upsert instead"
        )

    async def upsert(self, data: dict) -> StockMaster:
        """単一レコードの upsert はサポートしない.

        Raises:
            NotImplementedError: 常に発生
        """
        raise NotImplementedError(
            "Single upsert is not supported for StockMaster; use bulk_upsert instead"
        )

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
        insert_stmt = insert(table).values(records)

        # excluded は on_conflict_do_update 内で参照可能
        update_dict = {
            c.name: getattr(insert_stmt.excluded, c.name) for c in table.c if c.name != "id"
        }

        stmt = insert_stmt.on_conflict_do_update(index_elements=["stock_code"], set_=update_dict)

        try:
            await self.session.execute(stmt)
            await self.session.flush()
            return len(records)
        except SQLAlchemyError as e:
            logger.exception("bulk_upsert failed: %s", e)
            raise

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
            # 型安全性のため、getattrでデフォルト0を使用する
            rc: Any = getattr(result, "rowcount", 0)
            return int(rc or 0)
        except SQLAlchemyError as e:
            logger.exception("delete_all failed: %s", e)
            raise


__all__ = ["StockMasterRepository"]
