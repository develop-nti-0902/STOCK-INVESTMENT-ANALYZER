"""app.api.v1 package for versioned API routers."""

from fastapi import APIRouter

# v1 のサブルータをまとめて登録
from . import accounts as accounts_module
from . import auth as auth_module
from . import dividend_yield_history as dividend_yield_history_module
from . import edinet as edinet_module
from . import latest_stocks as latest_stocks_module
from . import nikkei225 as nikkei225_module
from . import relative_strength as relative_strength_module
from . import screening as screening_module
from . import stock_master as stock_master_module
from . import stock_price as stock_price_module

router = APIRouter()

router.include_router(edinet_module.router, prefix="/edinet")
router.include_router(nikkei225_module.router, prefix="/nikkei225")
router.include_router(stock_master_module.router, prefix="/stock-master")
router.include_router(stock_price_module.router, prefix="/stock-price")
router.include_router(dividend_yield_history_module.router, prefix="/dividend-yield-history")
router.include_router(auth_module.router, prefix="/auth")
router.include_router(accounts_module.router, prefix="/accounts")
router.include_router(latest_stocks_module.router, prefix="/views")
router.include_router(screening_module.router, prefix="/screening")
router.include_router(relative_strength_module.router, prefix="/relative-strength")

__all__ = ["router"]
