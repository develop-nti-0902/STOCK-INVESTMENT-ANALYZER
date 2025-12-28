"""app.api.v1 package for versioned API routers."""

from fastapi import APIRouter

# v1 のサブルータをまとめて登録
from . import batch as batch_module
from . import stock_data as stock_data_module

router = APIRouter()

router.include_router(batch_module.router, prefix="/batch")
router.include_router(stock_data_module.router, prefix="/stock-data")

__all__ = ["router"]
