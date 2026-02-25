"""Latest stocks view service module.

`latest_stocks_1d` ビューから単一銘柄の最新データを取得して返す機能を提供します.
"""

from __future__ import annotations

from app.exceptions.business import ServiceError
from app.repositories.latest_stocks_repository import LatestStocksRepository
from app.schemas.views import LatestStockResponse
from app.services.data_synchronization.views.base import BaseViewService


class LatestStocksService(BaseViewService):
    """`latest_stocks_1d`ビューからデータを取得するサービス.

    Attributes:
        repository: LatestStocksRepository のインスタンス
    """

    def __init__(self, repository: LatestStocksRepository):
        """サービスを初期化する.

        Args:
            repository: `LatestStocksRepository` のインスタンス
        """
        super().__init__()
        self.repository = repository

    async def get_latest_stock(self, symbol: str) -> LatestStockResponse:
        """指定銘柄の最新レコードを取得して `LatestStockResponse` で返す.

        Args:
            symbol: 銘柄コード

        Returns:
            LatestStockResponse: 取得した最新株価情報

        Raises:
            ServiceError: 銘柄が見つからない、または内部エラーが発生した場合
        """
        try:
            result = await self.repository.get_latest_stock_by_symbol(symbol)
            if result is None:
                raise ServiceError(message=f"Symbol {symbol} not found")

            return LatestStockResponse(**result)
        except ServiceError:
            raise
        except Exception as exc:
            self.logger.error(f"Failed to get latest stock for {symbol}: {exc}")
            raise ServiceError(message=f"Failed to get latest stock: {exc}") from exc


__all__ = ["LatestStocksService"]
