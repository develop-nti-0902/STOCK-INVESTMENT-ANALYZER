"""EDINET 損益・キャッシュフローサービスの orchestration モジュール.

fetcher, parser, converter, saver, file_manager を組み合わせて
文書取得→解析→変換→保存 を行います。
"""

from __future__ import annotations

from datetime import date
from typing import Any, List

from app.models.edinet_profit_and_loss import EdinetProfitAndLoss
from app.services.market_data.edinet.download_service import EdinetDownloadService
from app.services.market_data.edinet.file_manager import (
    EdinetFileManager as EdinetProfitAndLossFileManager,
)
from app.services.market_data.edinet.profit_and_loss.converter import EdinetProfitAndLossConverter
from app.services.market_data.edinet.profit_and_loss.parser import EdinetProfitAndLossParser
from app.services.market_data.edinet.profit_and_loss.saver import EdinetProfitAndLossSaver
from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetProfitAndLossService:
    """EDINET 損益・キャッシュフローのオーケストレーションサービス.

    Attributes:
        parser: XBRL パーサ
        converter: データ変換クラス
        saver: データ保存クラス
        file_manager: 一時ファイル管理ユーティリティ
        download_service: ダウンロード/抽出サービス
    """

    def __init__(
        self,
        parser: EdinetProfitAndLossParser,
        converter: EdinetProfitAndLossConverter,
        saver: EdinetProfitAndLossSaver,
        file_manager: EdinetProfitAndLossFileManager,
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
        # parser/saver の互換性を柔軟に扱う（parse_root が無ければ parse を使う等）
        parser_callable = getattr(self.parser, "parse_root", getattr(self.parser, "parse", None))
        saver_callable = getattr(self.saver, "save", getattr(self.saver, "save_single", None))
        pairs = []
        if parser_callable is not None and saver_callable is not None:
            pairs.append((parser_callable, self.converter, saver_callable))

        self._aggregate = EdinetAggregateUpdateService(
            download_service=download_service, parser_saver_pairs=pairs
        )

    async def get_latest_data(self, sec_code: str) -> Any:
        """指定の証券コードの最新の損益・キャッシュフローデータを取得する.

        Args:
            sec_code: 証券コード

        Returns:
            最新のデータ（存在しない場合は None）
        """
        return await self.saver.get_latest_by_sec_code(sec_code)

    async def get_by_period(self, sec_code: str, period_end_date: date) -> Any:
        """指定した期のレコードを返す.

        Args:
            sec_code: 証券コード
            period_end_date: 期末日

        Returns:
            該当するモデルまたは None
        """
        return await self.saver.repository.find_by_period(sec_code, period_end_date)

    async def get_annual_data(self, sec_code: str, fiscal_year: int) -> Any:
        """指定した会計年度のデータを返す.

        Args:
            sec_code: 証券コード
            fiscal_year: 会計年度（西暦）

        Returns:
            年次データのモデルまたは None
        """
        return await self.saver.repository.find_by_fiscal_year(sec_code, fiscal_year)

    async def get_multiple_latest(self, sec_codes: list[str]) -> List[EdinetProfitAndLoss]:
        """複数の証券コードについて最新レコードを一括で取得する.

        Args:
            sec_codes: 証券コードのリスト

        Returns:
            証券コードをキーとした最新レコードのマッピング
        """
        return await self.saver.repository.get_latest_by_sec_codes(sec_codes)

    async def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """古い一時ファイルをクリーンアップする.

        Args:
            max_age_hours: この時間より古いファイルを削除

        Returns:
            削除されたファイル数
        """
        work_dir = getattr(self.download_service, "work_dir", None)
        if work_dir is None:
            return 0
        return self.file_manager.cleanup_old_files(work_dir, max_age_hours=max_age_hours)


__all__ = ["EdinetProfitAndLossService"]
