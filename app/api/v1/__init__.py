"""app.api.v1 package for versioned API routers."""

from fastapi import APIRouter

# v1 のサブルータをまとめて登録
from . import batch as batch_module

router = APIRouter()

router.include_router(batch_module.router, prefix="/batch")

__all__ = ["router"]
