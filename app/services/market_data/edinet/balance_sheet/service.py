"""EDINET 貸借対照表サービスの orchestration モジュール.

fetcher, parser, converter, saver, file_manager を組み合わせて
文書取得→解析→変換→保存 を行います.
"""

from __future__ import annotations

from datetime import date

from app.services.market_data.edinet.balance_sheet.converter import EdinetBalanceSheetConverter
from app.services.market_data.edinet.balance_sheet.fetcher import EdinetDocumentFetcher
from app.services.market_data.edinet.balance_sheet.file_manager import EdinetFileManager
from app.services.market_data.edinet.balance_sheet.parser import EdinetBalanceSheetParser
from app.services.market_data.edinet.balance_sheet.saver import EdinetBalanceSheetSaver
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetService:
    """EDINET 貸借対照表のオーケストレーションサービス.

    Attributes:
        fetcher: 文書取得フェッチャ
        parser: XBRL パーサ
        converter: データ変換クラス
        saver: データ保存クラス
        file_manager: 一時ファイル管理ユーティリティ
    """

    def __init__(
        self,
        fetcher: EdinetDocumentFetcher,
        parser: EdinetBalanceSheetParser,
        converter: EdinetBalanceSheetConverter,
        saver: EdinetBalanceSheetSaver,
        file_manager: EdinetFileManager,
    ) -> None:
        """インスタンスを初期化する.

        Args:
            fetcher: 文書取得フェッチャ
            parser: XBRL パーサ
            converter: データ変換クラス
            saver: データ保存クラス
            file_manager: 一時ファイル管理ユーティリティ
        """
        self.fetcher = fetcher
        self.parser = parser
        self.converter = converter
        self.saver = saver
        self.file_manager = file_manager

    async def fetch_and_save(
        self,
        doc_id: str,
        sec_code: str,
        submission_date: date,
        filer_name: str | None = None,
    ):
        """単一文書を取得して解析し、データベースに保存する.

        過去5年分（current, prior1, prior2, prior3, prior4）のデータを取得し、
        それぞれUPSERTします。

        Note:
            トランザクション管理（commit/rollback）は呼び出し側で行う。

        Returns:
            保存後のモデルオブジェクトのリスト
        """
        xbrl_path = None
        try:
            ##########################################################
            # ドキュメント取得
            ##########################################################
            xbrl_path = await self.fetcher.fetch(doc_id)

            ##########################################################
            # XBRL 解析
            ##########################################################
            parsed = self.parser.parse(xbrl_path)

            ##########################################################
            # 5年分データの処理ループ
            ##########################################################
            results = []
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

                try:
                    ##########################################################
                    # Pydantic 変換（メタデータ付与）
                    ##########################################################
                    converter_data = {
                        **year_data,
                        "doc_id": doc_id,
                        "sec_code": sec_code,
                        "submission_date": submission_date,
                        "filer_name": filer_name,
                    }
                    pydantic_model = self.converter.to_pydantic(converter_data)

                    ##########################################################
                    # Saver 用辞書へ変換
                    ##########################################################
                    saver_record = self.converter.from_pydantic(pydantic_model)

                    ##########################################################
                    # 保存処理（save_single 呼び出し）
                    ##########################################################
                    result = await self.saver.save_single(saver_record)
                    results.append(result)
                    logger.debug(
                        "Saved data for %s, doc_id=%s, period=%s",
                        year_key,
                        doc_id,
                        period_end,
                    )

                except Exception as e:
                    ##########################################################
                    # 年次データ処理失敗時のログと例外伝播
                    ##########################################################
                    logger.exception(
                        "Failed to process year %s for doc_id=%s: %s",
                        year_key,
                        doc_id,
                        e,
                    )
                    # エラーを伝播させてトランザクションをロールバックする
                    raise

            ##########################################################
            # 処理結果を返す
            ##########################################################
            return results

        finally:
            ##########################################################
            # 一時ファイルのクリーンアップ
            ##########################################################
            try:
                if xbrl_path is not None:
                    parent = xbrl_path.parent
                    self.file_manager.cleanup(parent)
            except Exception:
                logger.exception("failed to cleanup temp files for %s", doc_id)

    async def get_latest_by_sec_code(self, sec_code: str):
        """指定した証券コードの最新レコードを返す.

        Args:
            sec_code: 証券コード

        Returns:
            最新のモデルまたは None
        """
        ##########################################################
        # リポジトリ経由で最新レコードを取得
        ##########################################################
        return await self.saver.repository.find_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date):
        """指定した期のレコードを返す.

        Args:
            sec_code: 証券コード
            period_end_date: 期末日

        Returns:
            該当するモデルまたは None
        """
        ##########################################################
        # 指定期のレコードをリポジトリから取得
        ##########################################################
        return await self.saver.repository.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int):
        """指定した会計年度のデータを返す.

        Args:
            sec_code: 証券コード
            fiscal_year: 会計年度（西暦）

        Returns:
            年次データのモデルまたは None
        """
        ##########################################################
        # 会計年度指定で年次データを取得
        ##########################################################
        return await self.saver.repository.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]):
        """複数の証券コードについて最新レコードを一括で取得する.

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            証券コードをキーとした最新レコードのマッピング
        """
        ##########################################################
        # 複数証券コードの最新レコードを一括取得
        ##########################################################
        return await self.saver.repository.get_latest_by_sec_codes(sec_codes)


__all__ = ["EdinetBalanceSheetService"]
