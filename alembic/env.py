"""非同期SQLAlchemyエンジン用の Alembic 環境設定。

この `env.py` は実行時の DB 接続 URL をプロジェクトの
`app.utils.database.get_database_url()` から取得します。
自動生成（autogenerate）ではプロジェクトの `Base.metadata` を参照します。

備考:
- ファイルエンコーディング: UTF-8
- タイムゾーン: プロジェクトは UTC 対応の DateTime を使用します。
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

# ローカルパッケージをインポートする前にプロジェクトルートを `sys.path` に追加
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logging.config import fileConfig  # noqa: E402

from sqlalchemy import pool  # noqa: E402
from sqlalchemy.engine import Connection  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncEngine,
    create_async_engine,
)

from alembic import context  # noqa: E402
from app.exceptions.system import SettingsValidationError  # noqa: E402

# プロジェクトのメタデータと DB ヘルパーをインポート
from app.models.base import Base  # プロジェクトのメタデータ  # noqa: E402
from app.utils.database import get_database_url  # noqa: E402

# Alembic の設定オブジェクト
# `alembic.context` は Alembic 実行時に動的に属性が追加されるため、
# 静的解析ツールがメンバーを認識できずに警告を出すことがあります。
# そのためここで必要な関数を getattr で取得してローカル変数に代入し、
# 以降はそれらを使って呼び出すことで静的解析の警告を回避します。
config = getattr(context, "config")
configure = getattr(context, "configure")
begin_transaction = getattr(context, "begin_transaction")
run_migrations = getattr(context, "run_migrations")
is_offline_mode = getattr(context, "is_offline_mode")

# .ini によるログ設定を適用
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 実行時の DB 接続 URL はプロジェクトのヘルパーから取得します
DATABASE_URL: Optional[str] = None
try:
    DATABASE_URL = get_database_url()
except SettingsValidationError:
    # 設定値のバリデーションに失敗した場合は None を設定し、
    # 下流で明示的にエラーにします。
    DATABASE_URL = None

if not DATABASE_URL:
    raise RuntimeError("Unable to obtain DB URL. Check get_database_url().")

# alembic の内部でも参照できるように設定
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーションを実行します。

    オフラインモードでは Engine を生成せず、URL のみでコンテキストを設定します。
    """
    url = config.get_main_option("sqlalchemy.url")
    configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with begin_transaction():
        run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # 与えられた接続上でマイグレーションを実行する共通処理
    configure(connection=connection, target_metadata=target_metadata)
    with begin_transaction():
        run_migrations()


async def run_async_migrations() -> None:
    """オンラインモードで非同期エンジンを使ってマイグレーションを実行します。"""
    connectable: AsyncEngine = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーションを実行するエントリポイント。"""
    asyncio.run(run_async_migrations())


if is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
