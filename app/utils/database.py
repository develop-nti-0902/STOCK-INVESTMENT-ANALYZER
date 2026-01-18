"""データベース接続とセッション管理のヘルパーモジュール。

SQLAlchemy の非同期エンジンとセッションメーカーの作成・管理を提供します。
FastAPI の ``Depends`` パターンで使用することを想定しています。

ノート:
        - ルートハンドラで ``get_db`` を依存関係として使用すると
            ``AsyncSession`` が取得できます。依存は正常終了時に commit を行い、
            例外発生時は rollback を行います。
        - Repository 層では commit を行わず、トランザクション境界は
            サービス層または API 層で管理してください。
"""

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_database_url() -> str:
    """
    データベース接続URLを取得

    環境変数から設定を読み込み、PostgreSQL接続URLを構築する。
    非同期ドライバ（asyncpg）を使用する。

    Returns:
        str: データベース接続URL（例: postgresql+asyncpg://user:pass@host:port/dbname）
    """
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


def create_engine() -> AsyncEngine:
    """
    非同期SQLAlchemyエンジンを作成

    接続プール設定:
    - pool_size: 基本接続数（デフォルト: 5）
    - max_overflow: 追加接続数（デフォルト: 10）
    - pool_pre_ping: 接続前のヘルスチェック有効化
    - echo: SQL実行ログ出力（開発環境のみ）

    Returns:
        AsyncEngine: SQLAlchemy非同期エンジン
    """
    settings = get_settings()
    database_url = get_database_url()

    engine = create_async_engine(
        database_url,
        echo=settings.DEBUG,  # 開発環境でのみSQLログ出力
        pool_size=settings.DB_POOL_SIZE,  # 環境変数から取得
        max_overflow=settings.DB_MAX_OVERFLOW,  # 環境変数から取得
        pool_pre_ping=True,  # 接続前のヘルスチェック
        pool_recycle=3600,  # 接続の自動リサイクル（1時間）
    )

    logger.info(
        "Database engine created",
        extra={
            "database": settings.DB_NAME,
            "host": settings.DB_HOST,
            "port": settings.DB_PORT,
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
        },
    )

    return engine


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """
    グローバルエンジンインスタンスを取得

    シングルトンパターンでエンジンを管理する。
    初回呼び出し時にエンジンを作成し、以降は同じインスタンスを返す。

    Returns:
        AsyncEngine: SQLAlchemy非同期エンジン
    """
    return create_engine()


@lru_cache(maxsize=1)
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    非同期セッションメーカーを取得

    セッション設定:
    - autocommit: False（明示的なコミット）
    - autoflush: False（明示的なフラッシュ）
    - expire_on_commit: False（コミット後もオブジェクトを有効に保つ）

    Returns:
        async_sessionmaker[AsyncSession]: セッションメーカー
    """
    engine = get_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    非同期DBセッションを提供（FastAPI Depends用）

    使用例:
        ```python
        from fastapi import Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.utils.database import get_db

        @router.get("/items/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            # dbセッションを使用してクエリ実行
            result = await db.execute(select(Item))
            return result.scalars().all()
        ```

    Yields:
        AsyncSession: 非同期DBセッション

    Note:
        トランザクション管理:
        - Repository層ではflush()のみを実行し、commit/rollbackは行いません
        - Service層/API層でトランザクション境界を管理します
        - このget_db()は、エンドポイント終了時に自動的にcommit/rollbackを実行します:
          * 正常終了時: 自動でcommit()
          * 例外発生時: 自動でrollback()
        - コンテキストマネージャとして動作し、必ずセッションをクローズします
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(
                "Database session error, rolling back",
                extra={"error": str(e), "error_type": type(e).__name__},
            )
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """
    データベース接続をクローズ

    アプリケーション終了時に呼び出し、全ての接続を適切にクローズする。
    FastAPIのlifespan eventで使用することを想定。

    使用例:
        ```python
        from contextlib import asynccontextmanager
        from fastapi import FastAPI

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            yield
            # Shutdown
            await close_db()

        app = FastAPI(lifespan=lifespan)
        ```
    """
    engine = get_engine()
    await engine.dispose()
    logger.info("Database engine disposed")
    # 再初期化を可能にするためキャッシュをクリア
    try:
        get_session_maker.cache_clear()
    except AttributeError:
        pass
    try:
        get_engine.cache_clear()
    except AttributeError:
        pass


async def flush_return(session: AsyncSession, return_value: Any) -> Any:
    """Session の flush を実行して指定値を返すヘルパー。

    Repository層ではコミットを行わず、flush（DBへの変更反映）のみを実行します。
    トランザクション管理（commit/rollback）はService層またはFastAPIのget_db()で行います。
    """
    # NOTE:
    # - Repository層はデータアクセスのみに専念し、トランザクション境界は
    #   上位層（Service層またはAPI層）で管理する設計です。
    # - flush()はDBに変更を反映しますが、トランザクションはコミットしません。
    # - 例外が発生した場合は、そのまま上位層に伝播させます。
    #   上位層でrollbackを実行してください。
    try:
        await session.flush()
        return return_value
    except Exception as e:
        logger.exception("DB flush failed: %s", e)
        raise


async def flush_return_with_log(
    session: AsyncSession, return_value: Any, log, msg: str, *args: Any
) -> Any:
    """`flush_return` を呼び出し、失敗時に共通的なログ出力を行うヘルパー。

    Args:
        session: 非同期セッション
        return_value: 成功時に返す値
        log: 呼び出し元のロガーインスタンス
        msg: 失敗時にログ出力するメッセージ（書式文字列）
        *args: メッセージのフォーマット引数

    Returns:
        指定された `return_value`

    Raises:
        発生した例外をそのまま再送出します。
    """
    try:
        return await flush_return(session, return_value)
    except Exception:
        # flush_return が例外を発生させた場合、ここでは呼び出し元固有のログを追記します。
        # rollbackは上位層（Service層またはFastAPIのget_db()）で実行されます。
        log.exception(msg, *args)
        raise
