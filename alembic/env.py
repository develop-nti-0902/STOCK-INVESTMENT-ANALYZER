import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
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
    """
    Alembic マイグレーション用のデータベースURLを取得する。

    非同期ドライバ（asyncpg）を使用してマイグレーションを実行します。

    Returns:
        str: Alembic 用の非同期データベースURL
    """
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
        f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    )


def run_migrations_offline() -> None:
    """'offline' モードでマイグレーションを実行する。

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
    """'online' モードでマイグレーションを実行する（非同期対応）。

    非同期エンジンを作成し、コンテキストに接続を関連付けます。

    """
    # 環境変数で sqlalchemy.url を上書き（非同期ドライバ）
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_alembic_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def do_run_migrations(connection: AsyncConnection) -> None:
        """非同期接続を使ってマイグレーションを実行する内部関数."""
        await connection.run_sync(do_configure_and_run)

    def do_configure_and_run(connection: Connection) -> None:
        """コンテキストを設定してマイグレーションを実行する同期関数."""
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

    async def run_async_migrations() -> None:
        """非同期エンジンとの接続を確立してマイグレーションを実行."""
        async with connectable.connect() as connection:
            await do_run_migrations(connection)

        await connectable.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
