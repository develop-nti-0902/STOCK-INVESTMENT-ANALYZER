"""日経225データ保存モジュール."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.market_data.nikkei225 import Nikkei2251dRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei225Saver:
    """日経225データを DB に保存するクラス."""

    def __init__(self, session: AsyncSession) -> None:
        """初期化.

        Args:
            session: 非同期 DB セッション
        """
        self.session = session
        self.repository = Nikkei2251dRepository(session)

    async def save(self, records: list[dict[str, Any]]) -> int:
        """バルク UPSERT でレコードを保存し、コミットする.

        Args:
            records: Converter.to_saver_records() の出力（辞書リスト）

        Returns:
            int: 保存（INSERT or UPDATE）されたレコード数

        Raises:
            Exception: DB 操作に失敗した場合（rollback 後に再 raise）
        """
        if not records:
            return 0
        try:
            saved = await self.repository.upsert_bulk(records)
            await self.session.commit()
            logger.info("Saved %d Nikkei225 records", saved)
            return saved
        except Exception:
            await self.session.rollback()
            logger.exception("Failed to save Nikkei225 records")
            raise
