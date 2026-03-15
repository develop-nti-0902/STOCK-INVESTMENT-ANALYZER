"""EDINET 配当メトリクスデータ保存層.

EdinetDividendMetricsRepository を使用して、データベースへの非同期保存を行います。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.edinet import EdinetDividendMetricsRepository
from app.schemas.market_data.edinet import EdinetDividendMetricsCreate
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DividendMetricsSaver:
    """配当メトリクスデータ保存クラス.

    EdinetDividendMetricsRepository を使用してデータベースに保存します。

    Attributes:
        repository: 配当メトリクスリポジトリ
        session: 非同期DBセッション
    """

    def __init__(
        self,
        repository: EdinetDividendMetricsRepository,
        session: AsyncSession,
    ) -> None:
        """初期化.

        Args:
            repository: 配当メトリクスリポジトリ
            session: 非同期DBセッション
        """
        self.repository = repository
        self.session = session

    async def save_many(
        self,
        records: list[EdinetDividendMetricsCreate],
    ) -> list[Any]:
        """複数の配当メトリクスを非同期で UPSERT 保存.

        unique_keys: (edinet_document_id, period_end_date)

        Args:
            records: 保存する配当メトリクスのリスト

        Returns:
            保存されたモデルオブジェクトのリスト

        Raises:
            ValueError: レコードリストが空の場合
        """
        if not records:
            logger.warning("save_many: 空のレコードリストが渡されました")
            return []

        # 辞書化（Repository の save_batch 用）
        records_dicts = [r.model_dump() for r in records]

        logger.info(f"DividendMetricsSaver: {len(records_dicts)} レコードを UPSERT 保存開始")

        # save_batch 実行
        result = await self.repository.save_batch(records_dicts)

        logger.info(f"DividendMetricsSaver: {len(result)} レコードを保存完了")
        return result


__all__ = ["DividendMetricsSaver"]
