from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# プロジェクト設定をインポートしてデータベースURLを構築
from app.utils.config import get_settings

# Alembic Config オブジェクト。.ini ファイルの値にアクセスできる
config = context.config  # type: ignore[attr-defined]

# Python ロギング用の設定ファイルを解釈
# この行で基本的なロガーをセットアップする
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# モデルの MetaData オブジェクトをここに追加
# 'autogenerate' サポート用
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# env.py の必要に応じて、設定から他の値を取得できる:
# my_important_option = config.get_main_option("my_important_option")
# ... など


def get_alembic_database_url() -> str:
    """
    Alembic マイグレーション用のデータベースURLを取得する。

    注意: Alembic は同期ドライバが必要。マイグレーションには asyncpg ではなく
    psycopg (同期版) を使用する。

    Returns:
        str: Alembic 用の同期データベースURL
    """
    settings = get_settings()
    return (
        f"postgresql+psycopg://{settings.DB_USER}:{settings.DB_PASSWORD}"
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
    """'online' モードでマイグレーションを実行する。

    このシナリオでは Engine を作成し、コンテキストに
    接続を関連付ける必要がある。

    """
    # 環境変数で sqlalchemy.url を上書き（同期ドライバ）
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_alembic_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
