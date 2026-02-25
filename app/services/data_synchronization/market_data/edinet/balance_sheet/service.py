"""EDINET 貸借対照表サービスの orchestration モジュール.

fetcher, parser, converter, saver, file_manager を組み合わせて
文書取得→解析→変換→保存 を行います.
"""

from __future__ import annotations

from datetime import date

from app.services.data_synchronization.market_data.edinet.balance_sheet.converter import (
    EdinetBalanceSheetConverter,
)
from app.services.data_synchronization.market_data.edinet.balance_sheet.parser import (
    EdinetBalanceSheetParser,
)
from app.services.data_synchronization.market_data.edinet.balance_sheet.saver import (
    EdinetBalanceSheetSaver,
)
from app.services.data_synchronization.market_data.edinet.file_manager import EdinetFileManager
from app.services.market_data.edinet.download_service import EdinetDownloadService
from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetService:
    """EDINET 貸借対照表のオーケストレーションサービス.

    Attributes:
        parser: XBRL パーサ
        converter: データ変換クラス
        saver: データ保存クラス
        file_manager: 一時ファイル管理ユーティリティ
        download_service: ダウンロード/抽出サービス
    """

    def __init__(
        self,
        parser: EdinetBalanceSheetParser,
        converter: EdinetBalanceSheetConverter,
        saver: EdinetBalanceSheetSaver,
        file_manager: EdinetFileManager,
        download_service: EdinetDownloadService,
    ) -> None:
        """インスタンスを初期化する.

        Args:
            parser: XBRL パーサ
            converter: データ変換クラス
            saver: データ保存クラス
            file_manager: 一時ファイル管理ユーティリティ
            download_service: ダウンロード/抽出サービス
        """
        self.parser = parser
        self.converter = converter
        self.saver = saver
        self.file_manager = file_manager

        self.download_service = download_service

        # 内部で統合サービスに委譲するインスタンスを作成
        parser_callable = getattr(self.parser, "parse_root", getattr(self.parser, "parse", None))
        saver_callable = getattr(self.saver, "save", getattr(self.saver, "save_single", None))
        pairs = []
        if parser_callable is not None and saver_callable is not None:
            pairs.append((parser_callable, self.converter, saver_callable))

        self._aggregate = EdinetAggregateUpdateService(
            download_service=download_service, parser_saver_pairs=pairs
        )

    async def get_latest_by_sec_code(self, sec_code: str):
        """指定した証券コードの最新レコードを返す.

        Args:
            sec_code: 証券コード

        Returns:
            最新のモデルまたは None
        """
        return await self.saver.repository.find_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date):
        """指定した期のレコードを返す.

        Args:
            sec_code: 証券コード
            period_end_date: 期末日

        Returns:
            該当するモデルまたは None
        """
        return await self.saver.repository.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int):
        """指定した会計年度のデータを返す.

        Args:
            sec_code: 証券コード
            fiscal_year: 会計年度（西暦）

        Returns:
            年次データのモデルまたは None
        """
        return await self.saver.repository.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]):
        """複数の証券コードについて最新レコードを一括で取得する.

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            証券コードをキーとした最新レコードのマッピング
        """
        return await self.saver.repository.get_latest_by_sec_codes(sec_codes)


__all__ = ["EdinetBalanceSheetService"]
