"""ビューからのデータ取得サービス."""

from __future__ import annotations

import logging

from app.exceptions.business import ServiceError
from app.repositories.latest_stocks_repository import LatestStocksRepository
from app.schemas.views import LatestStockResponse

logger = logging.getLogger(__name__)


class LatestStocksService:
    """latest_stocks_1dビューからデータを取得するサービス."""

    def __init__(self, repository: LatestStocksRepository):
        """初期化.

        Args:
            repository: latest_stocks_1dリポジトリ
        """
        self.repository = repository

    async def get_latest_stock(self, symbol: str) -> LatestStockResponse:
        """指定されたシンボルの最新株価情報を取得する.

        Args:
            symbol: 銘柄コード

        Returns:
            最新株価情報

        Raises:
            ServiceError: データ取得に失敗した場合
        """
        try:
            result = await self.repository.get_latest_stock_by_symbol(symbol)
            if result is None:
                raise ServiceError(message=f"Symbol {symbol} not found")

            return LatestStockResponse(**result)
        except ServiceError:
            raise
        except Exception as exc:
            logger.error(f"Failed to get latest stock for {symbol}: {exc}")
            raise ServiceError(
                message=f"Failed to get latest stock: {exc}"
            ) from exc


__all__ = ["LatestStocksService"]
