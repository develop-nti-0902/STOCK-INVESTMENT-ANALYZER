"""FastAPI アプリケーションのエントリポイントモジュール.

ライフサイクルハンドラ、例外ハンドラ、ルーティングの登録を行います。
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker

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

# ロガーの初期化（Lifespanで使用）
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """`on_event` の代替として動作するライフスパンハンドラ.

    起動時に以下の処理を行います：
    1. DB プールをウォームアップ
    2. ScreeningService を初期化し、業種設定キャッシュをロード

    終了時に `close_db` を呼んで DB リソースをクリーンアップします。

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

    # ScreeningService の初期化と業種設定キャッシュのロード
    try:
        logger.info("Initializing ScreeningService with industry config cache...")
        # 遅延インポート（循環依存を避けるため）
        # pylint: disable=import-outside-toplevel
        from app.api.v1.screening import DbFinancialQueryAdapter
        from app.repositories.market_data.stock_master import Sector33MasterRepository
        from app.repositories.screening.screening_result_repository import ScreeningResultRepository
        from app.services.screening.screening_service import ScreeningService

        engine = get_engine()
        maker = async_sessionmaker(bind=engine, expire_on_commit=False)

        # ScreeningService の生成
        fq_adapter = DbFinancialQueryAdapter(maker=maker)
        screening_service = ScreeningService(
            financial_query_service=fq_adapter,
            stock_master_maker=maker,
            screening_result_maker=maker,
            screening_result_factory=ScreeningResultRepository,
            sector_33_master_repo=None,  # 後で初期化時にセッション内で生成
        )

        # 業種設定キャッシュの初期化（セッション内で repo を生成）
        async with maker() as session:
            sector_33_repo = Sector33MasterRepository(session=session)
            # pylint: disable=protected-access
            screening_service._sector_33_master_repo = sector_33_repo
            await screening_service._init_industry_config_cache()

        logger.info("ScreeningService initialized with industry config cache")

        # app.state に保存
        _app.state.screening_service = screening_service

    except Exception as e:
        logger.error("Failed to initialize ScreeningService: %s", e)
        # キャッシュ初期化失敗でもアプリは起動するが、ログに警告を出力
        # （本番環境では設定エラーを厳格に扱う可能性あり）
        _app.state.screening_service = None

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

# 起動時に設定を一度だけ読み込み、アプリ状態に保持
app.state.settings = get_settings()

# CORS設定 (設定から読み込む)
settings = app.state.settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
    """ヘルスチェックエンドポイント.

    Returns:
        サービスの稼働状態を示す辞書
    """
    return {"status": "ok"}


# `app.api` が存在する場合は追加のルータを読み込みます
try:
    from app.api import router as api_router

    app.include_router(api_router, prefix="/api")
except ImportError:
    # 初期セットアップでは `app.api` が未実装の可能性があるため、
    # モジュール未検出（ImportError）の場合は無視します。
    pass

# 管理画面ルーターの登録
try:
    from app.api.admin import batch

    router: APIRouter = batch.router
    app.include_router(router)
except ImportError:
    # 管理画面が未実装の場合は無視
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


# Application lifecycle is handled by `lifespan` above
