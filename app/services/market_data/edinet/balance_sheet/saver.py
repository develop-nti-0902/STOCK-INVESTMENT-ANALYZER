"""EDINET 貸借対照表データSaver.

EdinetBalanceSheetRepository を使用して、データベースへの保存を行います。
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.edinet.edinet_balance_sheet_repository import (
    EdinetBalanceSheetRepository,
)
from app.services.core.savers.base_saver import BaseSaver
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetBalanceSheetSaver(BaseSaver[Dict[str, Any]]):
    """EDINET 貸借対照表データSaver.

    EdinetBalanceSheetRepository を使用してデータベースに保存します。

    Attributes:
        session: 非同期DBセッション
        repository: EDINET 貸借対照表リポジトリ
    """

    def __init__(self, session: AsyncSession) -> None:
        """初期化.

        Args:
            session: 非同期DBセッション
        """
        ##########################################################
        # 初期化処理（セッションとリポジトリの設定）
        ##########################################################
        super().__init__()
        self.session = session
        self.repository = EdinetBalanceSheetRepository(session)

    async def save_single(self, data: Dict[str, Any]) -> Any:
        """単一レコードを保存する.

        Args:
            data: 保存するデータ

        Returns:
            保存されたモデルオブジェクト
        """
        ##########################################################
        # 単一レコードの保存処理（リポジトリの upsert 呼び出し）
        ##########################################################
        return await self.repository.upsert(data)

    async def save(self, data: Dict[str, Any], **kwargs: Any) -> Any:
        """保存処理（save_single のエイリアス）.

        Args:
            data: 保存するデータ
            **kwargs: 追加パラメータ（未使用）

        Returns:
            保存されたモデルオブジェクト
        """
        ##########################################################
        # エイリアス経由の保存（内部で save_single を呼ぶ）
        ##########################################################
        return await self.save_single(data)

    async def save_batch(self, data_list: List[Dict[str, Any]], **kwargs: Any) -> int:
        """一括データ保存.

        Args:
            data_list: 保存するデータのリスト
            **kwargs: 追加パラメータ

        Returns:
            保存成功したレコード数
        """
        ##########################################################
        # 一括保存ループ（各レコードを upsert して成功数をカウント）
        ##########################################################
        saved_count = 0
        for data in data_list:
            try:
                ##########################################################
                # レコード保存（リポジトリ upsert）
                ##########################################################
                await self.repository.upsert(data)
                saved_count += 1
            except Exception as e:
                ##########################################################
                # 保存失敗時のログ出力と例外伝播
                ##########################################################
                logger.exception("Failed to save record: %s", e)
                # エラーを伝播させることで、呼び出し側でトランザクション管理を行う
                raise

        ##########################################################
        # 保存成功件数を返す
        ##########################################################
        return saved_count

    async def validate_data(self, data: Dict[str, Any]) -> bool:
        """データの妥当性を検証する.

        Args:
            data: 検証するデータ

        Returns:
            データが妥当な場合は True
        """
        ##########################################################
        # 必須フィールドの確認
        ##########################################################
        required_fields = [
            "doc_id",
            "sec_code",
            "submission_date",
            "period_end_date",
            "report_type",
        ]
        for field in required_fields:
            if field not in data:
                logger.warning("Missing required field: %s", field)
                return False

        ##########################################################
        # 検証結果を返す
        ##########################################################
        return True


__all__ = ["EdinetBalanceSheetSaver"]
