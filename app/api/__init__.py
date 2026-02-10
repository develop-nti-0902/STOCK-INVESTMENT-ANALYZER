"""API パッケージ. サブパッケージのルーターと依存関係を公開します."""

from fastapi import APIRouter

from app.api.v1 import router as v1_router

router = APIRouter()

# バージョン化されたルータを登録（新規導入: /api/v1/*）
router.include_router(v1_router, prefix="/v1")
