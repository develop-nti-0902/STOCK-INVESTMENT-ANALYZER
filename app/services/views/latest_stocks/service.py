from __future__ import annotations

from app.exceptions.business import ServiceError
from app.repositories.latest_stocks_repository import LatestStocksRepository
from app.schemas.views import LatestStockResponse
from app.services.views.base import BaseViewService


class LatestStocksService(BaseViewService):
    """latest_stocks_1dビューからデータを取得するサービス."""

    def __init__(self, repository: LatestStocksRepository):
        super().__init__()
        self.repository = repository

    async def get_latest_stock(self, symbol: str) -> LatestStockResponse:
        try:
            result = await self.repository.get_latest_stock_by_symbol(symbol)
            if result is None:
                raise ServiceError(message=f"Symbol {symbol} not found")

            return LatestStockResponse(**result)
        except ServiceError:
            raise
        except Exception as exc:
            self.logger.error(
                f"Failed to get latest stock for {symbol}: {exc}"
            )
            raise ServiceError(
                message=f"Failed to get latest stock: {exc}"
            ) from exc


__all__ = ["LatestStocksService"]
