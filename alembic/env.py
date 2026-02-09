"""Alembic environment for running migrations.

This module configures Alembic to run migrations using the project's
SQLAlchemy models and supports asynchronous engines.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncConnection, async_engine_from_config

from alembic import context

# モデルをインポートして autogenerate が検出できるようにする
from app.models import Base

# プロジェクト設定をインポートしてデータベースURLを構築
from app.utils.config import get_settings

# Alembic Config オブジェクト。.ini ファイルの値にアクセスできる
config = context.config  # type: ignore[attr-defined]

# Python ロギング用の設定ファイルを解釈
# この行で基本的なロガーをセットアップする
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# モデルの MetaData オブジェクトを設定（autogenerate サポート用）
target_metadata = Base.metadata

# env.py の必要に応じて、設定から他の値を取得できる:
# my_important_option = config.get_main_option("my_important_option")
# ... など


def get_alembic_database_url() -> str:
    """Alembic マイグレーション用のデータベースURLを取得する.

    非同期ドライバ（asyncpg）を使用してマイグレーションを実行します。

    Returns:
        str: Alembic 用の非同期データベースURL
    """
    # 環境変数 `DATABASE_URL` を最優先で使用する
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url

    # デフォルトはアプリ設定から `DATABASE_URL` を使う
    settings = get_settings()
    if getattr(settings, "DATABASE_URL", None):
        return settings.DATABASE_URL

    raise RuntimeError("No DATABASE_URL configured for Alembic migrations")


def run_migrations_offline() -> None:
    """'offline' モードでマイグレーションを実行する.

    Engine ではなく URL だけでコンテキストを設定する。
    ただし Engine も使用可能。Engine の作成をスキップすることで、
    DBAPI が利用可能である必要がなくなる。

    ここでの context.execute() 呼び出しは、指定された文字列を
    スクリプト出力に出力する。

    """
    # 環境変数からデータベースURLを取得（同期ドライバ）
    url = get_alembic_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """'online' モードでマイグレーションを実行する（非同期対応）.

    非同期エンジンを作成し、コンテキストに接続を関連付けます。

    """
    # 環境変数または設定から URL を取得
    configuration = config.get_section(config.config_ini_section, {})
    url = get_alembic_database_url()
    configuration["sqlalchemy.url"] = url

    # SQLite は同期エンジン + batch モードで実行する
    is_sqlite = url.startswith("sqlite:")
    if is_sqlite:
        # create synchronous engine for SQLite
        engine = create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=pool.NullPool
        )

        def do_configure_and_run(connection: Connection) -> None:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()

        with engine.connect() as connection:
            do_configure_and_run(connection)

        engine.dispose()
        return

    # 非SQLite（既存の asyncpg 等）の場合は非同期エンジンを使う
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_run_migrations(connection: AsyncConnection) -> None:
        await connection.run_sync(_do_configure_and_run)

    def _do_configure_and_run(connection: Connection) -> None:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations() -> None:
        async with connectable.connect() as connection:
            await do_run_migrations(connection)

        await connectable.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
