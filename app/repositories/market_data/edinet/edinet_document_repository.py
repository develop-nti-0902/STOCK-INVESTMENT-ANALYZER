"""EDINET Document メタデータ リポジトリ実装."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from app.models.market_data.edinet import EdinetDocument
from app.repositories.core.base import BaseRepository

logger = logging.getLogger(__name__)


class EdinetDocumentRepository(BaseRepository[EdinetDocument]):
    """EdinetDocument モデル用のリポジトリ。EDINET ドキュメントのメタデータを管理します。"""

    def __init__(self, session: AsyncSession):
        """セッションを受け取りリポジトリを初期化します."""
        super().__init__(session, model=EdinetDocument)

    async def find_by_doc_id(self, doc_id: str) -> Optional[EdinetDocument]:
        """ドキュメント ID で EDINET ドキュメントを検索します。

        Args:
            doc_id: EDINET ドキュメント ID

        Returns:
            見つかった EdinetDocument インスタンス（見つからない場合は None）
        """
        result = await self.session.execute(select(self.model).where(self.model.doc_id == doc_id))
        return result.scalar_one_or_none()

    async def find_by_sec_code(self, sec_code: str) -> List[EdinetDocument]:
        """証券コードに紐づく全ての EDINET ドキュメントを返します。

        Args:
            sec_code: 証券コード

        Returns:
            該当する EdinetDocument インスタンスのリスト
        """
        result = await self.session.execute(
            select(self.model)
            .where(self.model.sec_code == sec_code)
            .order_by(self.model.submission_date.desc())
        )
        return list(result.scalars().all())

    async def find_latest_by_sec_code(self, sec_code: str) -> Optional[EdinetDocument]:
        """証券コードで最新（submission_date が最新）の EDINET ドキュメントを返します。

        Args:
            sec_code: 証券コード

        Returns:
            見つかった EdinetDocument インスタンス（見つからない場合は None）
        """
        stmt = (
            select(self.model)
            .where(self.model.sec_code == sec_code)
            .order_by(self.model.submission_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_get(
        self,
        doc_id: str,
        sec_code: str,
        submission_date: date,
        report_type: str,
        **kwargs: Any,
    ) -> EdinetDocument:
        """指定の doc_id でドキュメントを検索し、存在しなければ新規作成します（upsert）。

        Args:
            doc_id: EDINET ドキュメント ID
            sec_code: 証券コード
            submission_date: 提出日
            report_type: 報告書タイプ
            **kwargs: 追加の属性（candidate_contexts, candidate_keys など）

        Returns:
            見つかったまたは新規作成された EdinetDocument インスタンス

        Raises:
            SQLAlchemyError: DB エラー
        """
        existing = await self.find_by_doc_id(doc_id)
        if existing:
            return existing

        data = {
            "doc_id": doc_id,
            "sec_code": sec_code,
            "submission_date": submission_date,
            "report_type": report_type,
            **kwargs,
        }
        return await self.upsert(data)

    async def upsert(self, data: dict) -> EdinetDocument:
        """与えられた辞書でレコードを upsert し、保存後のモデルを返します.

        内部で RETURNING 句を使用し、INSERT/UPDATE と結果取得を1クエリで実行します。

        Args:
            data: upsert するデータ辞書

        Returns:
            保存後の EdinetDocument インスタンス

        Raises:
            ValueError: data が空の場合
            SQLAlchemyError: DB エラー
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
            index_elements=["doc_id"],
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
            logger.exception("upsert failed for edinet_document")
            raise

    async def save_batch(self, data_list: list[dict]) -> list[EdinetDocument]:
        """複数レコードを一括 upsert し、保存後のモデルリストを返します.

        内部で RETURNING 句を使用し、複数 INSERT/UPDATE を1クエリで実行します。

        Args:
            data_list: upsert するデータのリスト（空リストも許容）

        Returns:
            保存後の EdinetDocument インスタンスのリスト

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
            index_elements=["doc_id"],
            set_=update_dict,
        ).returning(table)

        try:
            result = await self.session.execute(stmt)
            rows = result.fetchall()

            await self.session.flush()
            # Row オブジェクトを ORM モデルリストに変換
            return [self.model(**dict(row._mapping)) for row in rows]
        except SQLAlchemyError:
            logger.exception("save_batch_upsert failed for edinet_document")
            raise

    async def get_latest_by_sec_codes(self, sec_codes: List[str]) -> List[EdinetDocument]:
        """複数の証券コードについて各銘柄の最新ドキュメントを返します。

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            各証券コードの最新 EdinetDocument のリスト
        """
        if not sec_codes:
            return []

        stmt = (
            select(self.model)
            .where(self.model.sec_code.in_(sec_codes))
            .distinct(self.model.sec_code)
            .order_by(
                self.model.sec_code,
                self.model.submission_date.desc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_by_submission_date(self, submission_date: date) -> List[EdinetDocument]:
        """指定提出日に該当する全ドキュメントを返します。

        Args:
            submission_date: 提出日

        Returns:
            該当する EdinetDocument インスタンスのリスト
        """
        result = await self.session.execute(
            select(self.model)
            .where(self.model.submission_date == submission_date)
            .order_by(self.model.sec_code)
        )
        return list(result.scalars().all())

    async def find_by_date_range(self, start_date: date, end_date: date) -> List[EdinetDocument]:
        """指定期間内に提出されたドキュメントを返します。

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            該当する EdinetDocument インスタンスのリスト
        """
        result = await self.session.execute(
            select(self.model)
            .where(
                self.model.submission_date >= start_date,
                self.model.submission_date <= end_date,
            )
            .order_by(self.model.submission_date.desc(), self.model.sec_code)
        )
        return list(result.scalars().all())

    async def count_by_sec_code(self, sec_code: str) -> int:
        """指定証券コードに紐づくドキュメント件数を返します。

        Args:
            sec_code: 証券コード

        Returns:
            ドキュメント件数
        """
        stmt = select(sql_count()).select_from(self.model).where(self.model.sec_code == sec_code)
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
        except SQLAlchemyError:
            logger.exception("delete_all failed for edinet_document")
            raise
