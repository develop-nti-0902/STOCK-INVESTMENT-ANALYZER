"""ビュー関連のリポジトリ."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class LatestStocksRepository(BaseRepository):
    """latest_stocks_1dマテリアライズドビューへのアクセスを管理するリポジトリ."""

    def __init__(self, session: AsyncSession):
        """初期化.

        Args:
            session: データベースセッション
        """
        super().__init__(session)

    async def get_latest_stock_by_symbol(self, symbol: str) -> dict[str, Any] | None:
        """指定されたシンボルの最新株価情報を取得する.

        Args:
            symbol: 銘柄コード

        Returns:
            最新株価情報の辞書、見つからない場合はNone
        """
        query = text(
            """
            SELECT
                id,
                symbol,
                timestamp,
                open,
                high,
                low,
                close,
                adj_close,
                volume
            FROM latest_stocks_1d
            WHERE symbol = :symbol
            """
        )
        result = await self.session.execute(query, {"symbol": symbol})
        row = result.fetchone()

        if row is None:
            logger.debug("Symbol %s not found in latest_stocks_1d", symbol)
            return None

        # Row を辞書に変換
        return {
            "id": int(row.id),
            "symbol": str(row.symbol),
            "timestamp": (
                datetime.fromisoformat(str(row.timestamp))
                if isinstance(row.timestamp, str)
                else row.timestamp
            ),
            "open": Decimal(str(row.open)),
            "high": Decimal(str(row.high)),
            "low": Decimal(str(row.low)),
            "close": Decimal(str(row.close)),
            "adj_close": (Decimal(str(row.adj_close)) if row.adj_close is not None else None),
            "volume": int(row.volume),
        }


__all__ = ["LatestStocksRepository"]
