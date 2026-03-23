"""EDINET キャッシュフロー用 Repository 実装 (移動先)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from app.models.market_data.edinet import EdinetCashFlowStatement, EdinetDocument
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)

_UPSERT_CHUNK_SIZE = 2500


class EdinetCashFlowStatementRepository(BaseRepository[EdinetCashFlowStatement]):
    """EdinetCashFlowStatement モデル用のリポジトリ。"""

    def __init__(self, session: AsyncSession):
        """セッションを受け取りリポジトリを初期化します."""
        super().__init__(session, model=EdinetCashFlowStatement)

    async def find_latest_by_sec_code(self, sec_code: str) -> Optional[EdinetCashFlowStatement]:
        """指定証券コードの最新のキャッシュフロー（営業）レコードを返します。"""
        stmt = (
            select(self.model)
            .join(EdinetDocument, self.model.edinet_document_id == EdinetDocument.id)
            .where(EdinetDocument.sec_code == sec_code)
            .order_by(self.model.period_end_date.desc(), EdinetDocument.submission_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_period(
        self, sec_code: str, period_end_date: date
    ) -> Optional[EdinetCashFlowStatement]:
        """指定証券コードと期日でキャッシュフロー（営業）レコードを検索して返します。"""
        stmt = (
            select(self.model)
            .join(EdinetDocument, self.model.edinet_document_id == EdinetDocument.id)
            .where(
                EdinetDocument.sec_code == sec_code, self.model.period_end_date == period_end_date
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_edinet_document_id(
        self, edinet_document_id: int
    ) -> List[EdinetCashFlowStatement]:
        """EDINET ドキュメント ID に紐づくキャッシュフローレコードのリストを返します。

        Args:
            edinet_document_id: edinet_document テーブルの id

        Returns:
            該当する EdinetCashFlowStatement インスタンスのリスト
        """
        result = await self.session.execute(
            select(self.model)
            .where(self.model.edinet_document_id == edinet_document_id)
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def upsert(self, data: dict) -> EdinetCashFlowStatement:
        """与えられた辞書でレコードを upsert し、保存後のモデルを返します.

        内部で RETURNING 句を使用し、INSERT/UPDATE と結果取得を1クエリで実行します。
        """
        if not data:
            raise ValueError("data is required for upsert")

        table = self.model.__table__
        insert_stmt = insert(table).values(data)

        update_dict: dict[str, Any] = {
            c.name: getattr(insert_stmt.excluded, c.name)
            for c in table.c
            if c.name not in ("id", "created_at")
        }

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["edinet_document_id", "period_end_date"],
            set_=update_dict,
        ).returning(table)

        try:
            result = await self.session.execute(stmt)
            row = result.first()

            if row is None:
                raise RuntimeError("upsert succeeded but result not found")

            await self.session.flush()
            # Row オブジェクトを ORM モデルに変換
            return self.model(**dict(row._mapping))
        except SQLAlchemyError as e:
            logger.exception("edinet cash flow upsert failed: %s", e)
            raise

    async def save_batch(self, data_list: list[dict]) -> list[EdinetCashFlowStatement]:
        """複数レコードを一括 upsert し、保存後のモデルリストを返します.

        内部で RETURNING 句を使用し、複数 INSERT/UPDATE を1クエリで実行します。

        Args:
            data_list: upsert するデータのリスト (空リストも許容)

        Returns:
            保存後の EdinetCashFlowStatement インスタンスのリスト

        Raises:
            ValueError: data_list が None の場合
            SQLAlchemyError: DB エラー
        """
        if data_list is None:
            raise ValueError("data_list is required for save_batch_upsert")

        if not data_list:
            return []

        table = self.model.__table__
        all_results: list[EdinetCashFlowStatement] = []

        for i in range(0, len(data_list), _UPSERT_CHUNK_SIZE):
            chunk = data_list[i : i + _UPSERT_CHUNK_SIZE]
            insert_stmt = insert(table).values(chunk)

            update_dict: dict[str, Any] = {
                c.name: getattr(insert_stmt.excluded, c.name)
                for c in table.c
                if c.name not in ("id", "created_at")
            }

            stmt = insert_stmt.on_conflict_do_update(
                index_elements=["edinet_document_id", "period_end_date"],
                set_=update_dict,
            ).returning(table)

            try:
                result = await self.session.execute(stmt)
                rows = result.fetchall()
                all_results.extend([self.model(**dict(row._mapping)) for row in rows])
            except SQLAlchemyError as e:
                logger.exception("save_batch_upsert failed for edinet_cash_flow_statement: %s", e)
                raise

        await self.session.flush()
        return all_results

    async def get_latest_by_sec_codes(self, sec_codes: List[str]) -> List[EdinetCashFlowStatement]:
        """複数の証券コードについて各銘柄の最新キャッシュフローレコードを返します。"""
        if not sec_codes:
            return []

        stmt = (
            select(self.model)
            .join(EdinetDocument, self.model.edinet_document_id == EdinetDocument.id)
            .where(EdinetDocument.sec_code.in_(sec_codes))
            .distinct(EdinetDocument.sec_code)
            .order_by(
                EdinetDocument.sec_code,
                self.model.period_end_date.desc(),
                EdinetDocument.submission_date.desc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_fiscal_year(
        self, sec_code: str, fiscal_year: int
    ) -> List[EdinetCashFlowStatement]:
        """指定会計年度のキャッシュフローレコードを返します。"""
        result = await self.session.execute(
            select(self.model)
            .join(EdinetDocument, self.model.edinet_document_id == EdinetDocument.id)
            .where(EdinetDocument.sec_code == sec_code, self.model.fiscal_year == fiscal_year)
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def find_by_date_range(
        self, sec_code: str, start_date: date, end_date: date
    ) -> List[EdinetCashFlowStatement]:
        """指定期間内のキャッシュフローレコードを返します（start_date から end_date）。"""
        result = await self.session.execute(
            select(self.model)
            .join(EdinetDocument, self.model.edinet_document_id == EdinetDocument.id)
            .where(
                EdinetDocument.sec_code == sec_code,
                self.model.period_end_date >= start_date,
                self.model.period_end_date <= end_date,
            )
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def count_by_sec_code(self, sec_code: str) -> int:
        """指定証券コードに紐づくキャッシュフローレコード件数を返します。"""
        stmt = (
            select(sql_count())
            .select_from(self.model)
            .join(EdinetDocument, self.model.edinet_document_id == EdinetDocument.id)
            .where(EdinetDocument.sec_code == sec_code)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_all(self) -> int:
        """テーブル内の全レコードを削除する。

        Returns:
            int: 削除された件数

        Notes:
            トランザクションのコミットは Service 層で行ってください。
        """
        try:
            stmt = delete(self.model)
            result = await self.session.execute(stmt)
            await self.session.flush()
            rc: Any = getattr(result, "rowcount", 0)
            return int(rc or 0)
        except SQLAlchemyError as e:
            logger.exception("delete_all failed: %s", e)
            raise


__all__ = ["EdinetCashFlowStatementRepository"]
