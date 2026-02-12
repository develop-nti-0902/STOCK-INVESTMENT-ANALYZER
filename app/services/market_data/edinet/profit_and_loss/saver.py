"""EDINET 損益・キャッシュフローデータSaver.

EdinetProfitAndLossRepository を使用して、データベースへの保存を行います。
"""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.edinet_profit_and_loss_repository import EdinetProfitAndLossRepository
from app.services.core.savers.base_saver import BaseSaver
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EdinetProfitAndLossSaver(BaseSaver[Dict[str, Any]]):
    """EDINET 損益・キャッシュフローデータSaver.

    EdinetProfitAndLossRepository を使用してデータベースに保存します。

    Attributes:
        session: 非同期DBセッション
        repository: EDINET 損益・キャッシュフローリポジトリ
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
        self.repository = EdinetProfitAndLossRepository(session)

    async def save_single(self, data: Dict[str, Any]) -> Any:
        """単一レコードを保存する.

        Args:
            data: 保存するデータ

        Returns:
            保存されたモデルオブジェクト
        """
        ##########################################################
        # 入力データのバリデーション
        ##########################################################
        if not data:
            raise ValueError("data is required")

        required_fields = ["sec_code", "period_end_date"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field '{field}' is missing")

        ##########################################################
        # UPSERT実行（既存レコードがあれば更新、なければ新規作成）
        ##########################################################
        logger.debug(f"Upserting profit and loss data for {data.get('sec_code')}")
        result = await self.repository.upsert(data)
        logger.info(f"Successfully upserted profit and loss data: {result.id}")

        return result

    async def save_batch(self, data_list: List[Dict[str, Any]], **kwargs: Any) -> Any:
        """バッチでレコードを保存する.

        Args:
            data_list: 保存するデータのリスト

        Returns:
            保存されたモデルオブジェクトのリスト
        """
        ##########################################################
        # 各レコードを順次処理
        ##########################################################
        results = []
        for data in data_list:
            try:
                result = await self.save_single(data)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to save record: {data}. Error: {e}")
                # 個別の失敗があっても処理を継続
                continue

        logger.info(f"Batch save completed. {len(results)} of {len(data_list)} records saved.")
        return results

    async def save(self, data: Dict[str, Any], **kwargs: Any) -> Any:
        """保存処理（save_single のエイリアス）.

        Args:
            data: 保存するデータ
            **kwargs: 追加パラメータ（未使用）

        Returns:
            保存されたモデルオブジェクト
        """
        return await self.save_single(data)

    async def exists(self, sec_code: str, period_end_date: Any) -> bool:
        """指定された条件でレコードが存在するかチェックする.

        Args:
            sec_code: 証券コード
            period_end_date: 決算期末日

        Returns:
            レコードが存在する場合は True
        """
        result = await self.repository.find_by_period(sec_code, period_end_date)
        return result is not None

    async def get_latest_by_sec_code(self, sec_code: str) -> Any:
        """指定された証券コードの最新レコードを取得する.

        Args:
            sec_code: 証券コード

        Returns:
            最新のレコード（存在しない場合は None）
        """
        return await self.repository.find_latest_by_sec_code(sec_code)

    def validate_data_sync(self, data: Dict[str, Any]) -> bool:
        """データの妥当性を検証する（BaseSaver の同期検証メソッド実装）.

        Args:
            data: 検証するデータ

        Returns:
            データが妥当な場合は True
        """
        if not isinstance(data, dict):
            return False

        required_fields = ["sec_code", "period_end_date"]
        return all(field in data and data[field] is not None for field in required_fields)


__all__ = ["EdinetProfitAndLossSaver"]
