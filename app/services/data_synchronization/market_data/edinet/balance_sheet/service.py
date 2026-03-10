"""EDINET 貸借対照表サービスのorchestrationモジュール.

fetcher, parser, converter, saver, file_manager を組み合わせて
文書取得→解析→変換→保存 を行います。
"""

from __future__ import annotations

from datetime import date
from typing import Any, List

from app.models.market_data.edinet import EdinetBalanceSheet
from app.services.data_synchronization.market_data.edinet.balance_sheet.converter import (
    EdinetBalanceSheetConverter,
)
from app.services.data_synchronization.market_data.edinet.balance_sheet.parser import (
    EdinetBalanceSheetParser,
)
from app.services.data_synchronization.market_data.edinet.balance_sheet.saver import (
    EdinetBalanceSheetSaver,
)
from app.services.data_synchronization.market_data.edinet.download_service import (
    EdinetDownloadService,
)
from app.services.data_synchronization.market_data.edinet.file_manager import (
    EdinetFileManager as EdinetBalanceSheetFileManager,
)
from app.services.data_synchronization.market_data.edinet.update_service import (
    EdinetAggregateUpdateService,
)
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
        file_manager: EdinetBalanceSheetFileManager,
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
        """指定の証券コードの最新の貸借対照表データを取得する.

        Args:
            sec_code: 証券コード

        Returns:
            最新のデータ（存在しない場合は None）
        """
        return await self.saver.exists(sec_code, None)

    async def get_by_period(self, sec_code: str, period_end_date: date) -> Any:
        """指定した期のレコードを返す.

        Args:
            sec_code: 証券コード
            period_end_date: 期末日

        Returns:
            レコード（存在しない場合は None）
        """
        return await self.saver.repository.find_by_period(sec_code, period_end_date)


__all__ = ["EdinetBalanceSheetService"]
