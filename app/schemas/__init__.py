"""Pydantic スキーマの公開パッケージ.

このモジュールはプロジェクト内で利用可能な主要な Pydantic スキーマをまとめて
エクスポートします。
"""

from pydantic import BaseModel

from app.schemas.accounts import (  # noqa: F401
    AccountLoginRequest,
    AccountRegisterRequest,
    AccountResponse,
    AccountUpdateRequest,
    PasswordChangeRequest,
    TokenResponse,
)
from app.schemas.core.base import (
    BaseRequestSchema,
    BaseResponseSchema,
    BaseSchema,
    PaginationRequestSchema,
    PaginationResponseSchema,
)

# backward-compat: expose module names that tests (and older imports) may reference
from app.schemas.market_data.edinet import (  # noqa: F401
    EdinetBalanceSheetBase,
    EdinetBalanceSheetCreate,
    EdinetBalanceSheetLatest,
    EdinetBalanceSheetRead,
    EdinetProfitAndLossBase,
    EdinetProfitAndLossCreate,
    EdinetProfitAndLossLatest,
    EdinetProfitAndLossRead,
    edinet_balance_sheet,
    edinet_cash_flow_statement,
    edinet_profit_and_loss,
    edinet_stock_dividend,
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
    """ヘルスチェック用レスポンススキーマ.

    Attributes:
        status (str): サービスの稼働状態を表す文字列
    """

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

# accounts schemas
__all__.extend(
    [
        "AccountRegisterRequest",
        "AccountLoginRequest",
        "AccountUpdateRequest",
        "PasswordChangeRequest",
        "AccountResponse",
        "TokenResponse",
    ]
)

# edinet schemas
__all__.extend(
    [
        "EdinetBalanceSheetBase",
        "EdinetBalanceSheetCreate",
        "EdinetBalanceSheetRead",
        "EdinetBalanceSheetLatest",
        "EdinetProfitAndLossBase",
        "EdinetProfitAndLossCreate",
        "EdinetProfitAndLossRead",
        "EdinetProfitAndLossLatest",
        "edinet_balance_sheet",
        "edinet_cash_flow_statement",
        "edinet_profit_and_loss",
        "edinet_stock_dividend",
    ]
)
