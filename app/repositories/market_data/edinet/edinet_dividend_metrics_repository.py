"""edinet_dividend_metrics repository."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.edinet import EdinetDividendMetrics, EdinetDocument
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)


class EdinetDividendMetricsRepository(BaseRepository[EdinetDividendMetrics]):
    """EdinetDividendMetrics モデル用のリポジトリ。"""

    def __init__(self, session: AsyncSession):
        """セッションを受け取りリポジトリを初期化します."""
        super().__init__(session, model=EdinetDividendMetrics)

    async def find_latest_by_sec_code(self, sec_code: str) -> Optional[EdinetDividendMetrics]:
        """指定証券コードの最新の配当メトリクスレコードを返します（存在しなければ None）。"""
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
    ) -> Optional[EdinetDividendMetrics]:
        """指定証券コードと期日で配当メトリクスレコードを検索して返します。"""
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
    ) -> List[EdinetDividendMetrics]:
        """EDINET ドキュメント ID に紐づく配当メトリクスレコードのリストを返します。

        Args:
            edinet_document_id: edinet_document テーブルの id

        Returns:
            該当する EdinetDividendMetrics インスタンスのリスト
        """
        result = await self.session.execute(
            select(self.model)
            .where(self.model.edinet_document_id == edinet_document_id)
            .order_by(self.model.period_end_date.desc())
        )
        return list(result.scalars().all())

    async def find_latest_by_edinet_document_id(
        self, edinet_document_id: int
    ) -> Optional[EdinetDividendMetrics]:
        """EDINET ドキュメント ID に紐づく最新の配当メトリクスレコードを返します。

        Args:
            edinet_document_id: edinet_document テーブルの id

        Returns:
            見つかった EdinetDividendMetrics インスタンス（見つからない場合は None）
        """
        stmt = (
            select(self.model)
            .where(self.model.edinet_document_id == edinet_document_id)
            .order_by(self.model.period_end_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, data: dict[str, Any]) -> EdinetDividendMetrics:
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
        except SQLAlchemyError:
            logger.exception("upsert failed for edinet_dividend_metrics")
            raise

    async def save_batch(self, data_list: list[dict[str, Any]]) -> list[EdinetDividendMetrics]:
        """複数レコードを一括 upsert し、保存後のモデルリストを返します.

        内部で RETURNING 句を使用し、複数 INSERT/UPDATE を1クエリで実行します。

        Args:
            data_list: upsert するデータのリスト (空リストも許容)

        Returns:
            保存後の EdinetDividendMetrics インスタンスのリスト

        Raises:
            ValueError: data_list が None の場合
            SQLAlchemyError: DB エラー
        """
        if data_list is None:
            raise ValueError("data_list is required for save_batch_upsert")

        if not data_list:
            return []

        table = self.model.__table__
        insert_stmt = insert(table).values(data_list)

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

            await self.session.flush()
            # Row オブジェクトを ORM モデルリストに変換
            return [self.model(**dict(row._mapping)) for row in rows]
        except SQLAlchemyError:
            logger.exception("save_batch_upsert failed for edinet_dividend_metrics")
            raise


__all__ = ["EdinetDividendMetricsRepository"]
