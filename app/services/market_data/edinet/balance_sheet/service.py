"""EDINET 貸借対照表サービスの orchestration モジュール.

fetcher, parser, file_manager, repository を組み合わせて
文書取得→解析→UPSERT を行います.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.edinet_balance_sheet_repository import EdinetBalanceSheetRepository
from app.services.market_data.edinet.balance_sheet.fetcher import EdinetDocumentFetcher
from app.services.market_data.edinet.balance_sheet.file_manager import EdinetFileManager
from app.services.market_data.edinet.balance_sheet.parser import EdinetBalanceSheetParser
from app.utils.database import get_session_maker
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetService:
    """EDINET 貸借対照表のオーケストレーションサービス.

    Attributes:
        fetcher: 文書取得フェッチャ
        parser: XBRL パーサ
        file_manager: 一時ファイル管理ユーティリティ
        session_maker: DB セッションファクトリ
        repo_class: リポジトリクラス
    """

    def __init__(
        self,
        fetcher: EdinetDocumentFetcher,
        parser: EdinetBalanceSheetParser,
        file_manager: EdinetFileManager,
        session_maker: Optional[Callable[[], Any]] = None,
        repo_class: Callable[[AsyncSession], EdinetBalanceSheetRepository] = (
            EdinetBalanceSheetRepository
        ),
    ) -> None:
        """インスタンスを初期化する."""
        self.fetcher = fetcher
        self.parser = parser
        self.file_manager = file_manager
        self.session_maker = session_maker or get_session_maker()
        self.repo_class = repo_class

    async def fetch_and_save_single(
        self,
        doc_id: str,
        sec_code: str,
        submission_date: date,
        filer_name: Optional[str] = None,
    ):
        """単一文書を取得して解析し、データベースに保存する.

        過去5年分（current, prior1, prior2, prior3, prior4）のデータを取得し、
        それぞれUPSERTします。

        Returns:
            保存後のモデルオブジェクトのリスト
        """
        xbrl_path = None
        try:
            xbrl_path = await self.fetcher.fetch(doc_id)
            parsed = self.parser.parse(xbrl_path)

            results = []
            # 5年分のデータをそれぞれUPSERT
            for year_key in [
                "current",
                "prior1",
                "prior2",
                "prior3",
                "prior4",
            ]:
                year_data = parsed.get(year_key)
                if not year_data:
                    logger.debug(
                        "No data for %s in doc_id=%s, skipping",
                        year_key,
                        doc_id,
                    )
                    continue

                period_end = year_data.get("period_end")
                if not period_end:
                    logger.warning(
                        "period_end missing for %s in doc_id=%s",
                        year_key,
                        doc_id,
                    )
                    continue

                # fiscal_year を簡易算出
                try:
                    fiscal_year = int(str(period_end).split("-")[0])
                except Exception:
                    fiscal_year = None

                payload = {
                    "doc_id": doc_id,
                    "sec_code": sec_code,
                    "filer_name": filer_name,
                    "submission_date": submission_date,
                    "period_end_date": period_end,
                    "fiscal_year": fiscal_year,
                    "report_type": "annual",
                    "total_assets": year_data.get("assets"),
                    "total_liabilities": year_data.get("liabilities"),
                    "total_equity": year_data.get("equity"),
                    "is_consolidated": year_data.get("consolidation"),
                }

                result = await self.upsert_balance_sheet(payload)
                results.append(result)

            return results

        finally:
            # 一時ファイルが作られていれば、file_manager でクリーンアップを試みる
            try:
                if xbrl_path is not None:
                    parent = xbrl_path.parent
                    self.file_manager.cleanup(parent)
            except Exception:
                logger.exception("failed to cleanup temp files for %s", doc_id)

    async def upsert_balance_sheet(self, data: dict):
        """Repository を使って UPSERT を実行しトランザクションを管理する."""
        session_maker = self.session_maker
        async with session_maker() as session:  # type: ignore[call-arg]
            try:
                repo = self.repo_class(session)
                res = await repo.upsert(data)
                await session.commit()
                return res
            except Exception:
                await session.rollback()
                logger.exception("upsert failed for %s", data.get("doc_id"))
                raise

    async def get_latest_by_sec_code(self, sec_code: str):
        """指定した証券コードの最新レコードを返す.

        Args:
            sec_code: 証券コード

        Returns:
            最新のモデルまたは None
        """
        session_maker = self.session_maker
        async with session_maker() as session:  # type: ignore[call-arg]
            repo = self.repo_class(session)
            return await repo.find_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date):
        """指定した期のレコードを返す.

        Args:
            sec_code: 証券コード
            period_end_date: 期末日

        Returns:
            該当するモデルまたは None
        """
        session_maker = self.session_maker
        async with session_maker() as session:  # type: ignore[call-arg]
            repo = self.repo_class(session)
            return await repo.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int):
        """指定した会計年度のデータを返す.

        Args:
            sec_code: 証券コード
            fiscal_year: 会計年度（西暦）

        Returns:
            年次データのモデルまたは None
        """
        session_maker = self.session_maker
        async with session_maker() as session:  # type: ignore[call-arg]
            repo = self.repo_class(session)
            return await repo.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]):
        """複数の証券コードについて最新レコードを一括で取得する.

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            証券コードをキーとした最新レコードのマッピング
        """
        session_maker = self.session_maker
        async with session_maker() as session:  # type: ignore[call-arg]
            repo = self.repo_class(session)
            return await repo.get_latest_by_sec_codes(sec_codes)


__all__ = ["EdinetBalanceSheetService"]
