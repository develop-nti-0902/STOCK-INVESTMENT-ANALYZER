from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.exceptions import (
    AppException,
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.schemas import HealthResponse
from app.utils.config import get_settings
from app.utils.database import close_db, get_engine
from app.utils.logger import get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """`on_event` の代替として動作するライフスパンハンドラ。

    起動時に DB プールをウォームアップし、終了時に `close_db` を呼んで
    DB リソースをクリーンアップします。

    引数の `_app` は FastAPI が渡すアプリインスタンスですが本関数内で
    使用しないため先頭にアンダースコアを付けて未使用を明示しています。
    """
    # 起動処理
    try:
        engine = get_engine()
        try:
            conn = await engine.connect()
            await conn.close()
            logger.info("Database pool warmed up on startup")
        except SQLAlchemyError as e:
            logger.error("Failed to warm up DB pool on startup: %s", e)
    except SQLAlchemyError as e:
        logger.error("Failed to initialize DB engine on startup: %s", e)

    try:
        yield
    finally:
        # 終了処理
        try:
            await close_db()
            logger.info("Database engine disposed on shutdown")
        except SQLAlchemyError as e:
            logger.error("Error while disposing DB engine on shutdown: %s", e)


app = FastAPI(title="Stock Investment Analyzer API", lifespan=lifespan)

# ロガー
logger = get_logger(__name__)

# 起動時に設定を一度だけ読み込み、アプリ状態に保持
app.state.settings = get_settings()

# 例外ハンドラの登録
app.add_exception_handler(
    AppException,
    app_exception_handler,
)
app.add_exception_handler(
    HTTPException,
    http_exception_handler,
)
app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


# `app.api` が存在する場合は追加のルータを読み込みます
try:
    from app.api import router as api_router

    app.include_router(api_router, prefix="/api")
except ImportError:
    # 初期セットアップでは `app.api` が未実装の可能性があるため、
    # モジュール未検出（ImportError）の場合は無視します。
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


# Application lifecycle is handled by `lifespan` above
