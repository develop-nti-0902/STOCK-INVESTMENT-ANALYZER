"""app.api.v1 package for versioned API routers."""

from fastapi import APIRouter

# v1 のサブルータをまとめて登録
from . import accounts as accounts_module
from . import auth as auth_module
from . import edinet as edinet_module
from . import stock_master as stock_master_module
from . import stock_price as stock_price_module
from . import views as views_module

router = APIRouter()

router.include_router(edinet_module.router, prefix="/edinet")
router.include_router(stock_master_module.router, prefix="/stock-master")
router.include_router(stock_price_module.router, prefix="/stock-price")
router.include_router(auth_module.router, prefix="/auth")
router.include_router(accounts_module.router, prefix="/accounts")
router.include_router(views_module.router, prefix="/views")

__all__ = ["router"]
