# Pydantic schemas package
from pydantic import BaseModel

from app.schemas.base import (
    BaseRequestSchema,
    BaseResponseSchema,
    BaseSchema,
    PaginationRequestSchema,
    PaginationResponseSchema,
)
from app.schemas.stock_data import (
    StockPrice1D,
    StockPrice1H,
    StockPrice1M,
    StockPrice1MO,
    StockPrice1WK,
    StockPrice5M,
    StockPrice15M,
    StockPriceBase,
    StockPriceBatch,
    StockPriceCreate,
    StockPriceResponse,
)


class HealthResponse(BaseModel):
    status: str


__all__ = [
    "BaseSchema",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "PaginationRequestSchema",
    "PaginationResponseSchema",
    "HealthResponse",
    "StockPriceBase",
    "StockPriceCreate",
    "StockPriceResponse",
    "StockPriceBatch",
    "StockPrice1M",
    "StockPrice5M",
    "StockPrice15M",
    "StockPrice1H",
    "StockPrice1D",
    "StockPrice1WK",
    "StockPrice1MO",
]
