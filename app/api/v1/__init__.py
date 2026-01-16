"""app.api.v1 package for versioned API routers."""

from fastapi import APIRouter

# v1 のサブルータをまとめて登録
from . import auth as auth_module
from . import batch as batch_module
from . import stock_master as stock_master_module
from . import stock_price as stock_price_module

router = APIRouter()

router.include_router(batch_module.router, prefix="/batch")
router.include_router(stock_master_module.router, prefix="/stock-master")
router.include_router(stock_price_module.router, prefix="/stock-price")
router.include_router(auth_module.router, prefix="/auth")

__all__ = ["router"]
