"""初期データベーススキーマ（Alembic リビジョン）

Revision ID: 0001_initial_database_schema
Revises:
Create Date: 2025-12-07 00:00:00.000000

このファイルは Alembic 用の初期マイグレーションを定義します。
ドキュメント文字列とコメントは日本語で記載しています。
"""

# pylint: disable=invalid-name
# 注意: Alembic の規約に従いモジュールレベルの変数名
# (`revision`, `down_revision` など) は小文字を使用します。linter の
# invalid-name 警告をこのファイル単位で抑制しています。
#
# Alembic の `op` モジュールは実行時に動的に属性（`create_table` 等）を提供するため、
# 静的解析ツール（pylint/mypy 等）が "module has no member" と誤検出することがあります。
# このファイルではその誤検出を抑制するために `no-member` を無効化します。
# pylint: disable=no-member

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# リビジョン識別子（Alembic によって使用されます）
revision = "0001_initial_database_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 銘柄マスタ（管理テーブル） - create_management_tables.sql に準拠
    op.create_table(
        "stock_master",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=10), nullable=False),
        sa.Column("stock_name", sa.String(length=100), nullable=False),
        sa.Column("market_category", sa.String(length=50), nullable=True),
        sa.Column("sector_code_33", sa.String(length=10), nullable=True),
        sa.Column("sector_name_33", sa.String(length=100), nullable=True),
        sa.Column("sector_code_17", sa.String(length=10), nullable=True),
        sa.Column("sector_name_17", sa.String(length=100), nullable=True),
        sa.Column("scale_code", sa.String(length=10), nullable=True),
        sa.Column("scale_category", sa.String(length=50), nullable=True),
        sa.Column("data_date", sa.String(length=8), nullable=True),
        sa.Column(
            "is_active", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=text("now()"),
        ),
    )
    op.create_index("idx_stock_master_code", "stock_master", ["stock_code"])
    op.create_index("idx_stock_master_active", "stock_master", ["is_active"])
    op.create_index(
        "idx_stock_master_market", "stock_master", ["market_category"]
    )
    op.create_index(
        "idx_stock_master_sector_33", "stock_master", ["sector_code_33"]
    )
    op.create_unique_constraint(
        "uix_stock_master_stock_code", "stock_master", ["stock_code"]
    )

    # 銘柄マスタ更新履歴テーブル
    op.create_table(
        "stock_master_updates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("update_type", sa.String(length=20), nullable=False),
        sa.Column("total_stocks", sa.Integer(), nullable=False),
        sa.Column(
            "added_stocks", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "updated_stocks", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "removed_stocks", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # バッチ実行サマリテーブル
    op.create_table(
        "batch_executions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("total_stocks", sa.Integer(), nullable=False),
        sa.Column(
            "processed_stocks", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "successful_stocks",
            sa.Integer(),
            nullable=True,
            server_default="0",
        ),
        sa.Column(
            "failed_stocks", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "start_time",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=text("now()"),
        ),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=text("now()"),
        ),
    )
    op.create_index(
        "idx_batch_executions_status", "batch_executions", ["status"]
    )
    op.create_index(
        "idx_batch_executions_batch_type", "batch_executions", ["batch_type"]
    )
    op.create_index(
        "idx_batch_executions_start_time", "batch_executions", ["start_time"]
    )

    # バッチ実行の詳細テーブル（各銘柄ごとの実行結果）
    op.create_table(
        "batch_execution_details",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_execution_id", sa.Integer(), nullable=False),
        sa.Column("stock_code", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "records_inserted", sa.Integer(), nullable=True, server_default="0"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["batch_execution_id"], ["batch_executions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_batch_execution_details_batch_id",
        "batch_execution_details",
        ["batch_execution_id"],
    )
    op.create_index(
        "idx_batch_execution_details_status",
        "batch_execution_details",
        ["status"],
    )
    op.create_index(
        "idx_batch_execution_details_stock_code",
        "batch_execution_details",
        ["stock_code"],
    )
    op.create_index(
        "idx_batch_execution_details_batch_stock",
        "batch_execution_details",
        ["batch_execution_id", "stock_code"],
    )

    # 株価データテーブル群: scripts/databaseSetup/sql/create_stock_tables.sql の定義に準拠
    def _create_intraday_sql(table_name):
        # DESC 指定のインデックスや CHECK 制約など、SQL を直接実行して制約を追加します
        op.create_table(
            table_name,
            sa.Column(
                "id", sa.Integer(), primary_key=True, autoincrement=True
            ),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("datetime", sa.DateTime(timezone=True), nullable=False),
            sa.Column("open", sa.Numeric(), nullable=False),
            sa.Column("high", sa.Numeric(), nullable=False),
            sa.Column("low", sa.Numeric(), nullable=False),
            sa.Column("close", sa.Numeric(), nullable=False),
            sa.Column(
                "volume", sa.BigInteger(), nullable=False, server_default="0"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["symbol"], ["stock_master.stock_code"], ondelete="CASCADE"
            ),
        )
        # 一意制約
        op.create_unique_constraint(
            f"uq_{table_name}_symbol_datetime",
            table_name,
            ["symbol", "datetime"],
        )
        # 基本的なインデックス
        op.create_index(f"idx_{table_name}_symbol", table_name, ["symbol"])
        op.create_index(f"idx_{table_name}_datetime", table_name, ["datetime"])
        # symbol と datetime DESC による複合インデックスを作成
        sql = (
            f"CREATE INDEX IF NOT EXISTS "
            f"idx_{table_name}_symbol_datetime_desc "
            f"ON {table_name} (symbol, datetime DESC);"
        )
        op.execute(sql)
        # 価格／ボリュームに関する CHECK 制約を追加
        sql = (
            f"ALTER TABLE {table_name} ADD CONSTRAINT "
            f"chk_{table_name}_non_negative_prices "
            f"CHECK (open >= 0 AND high >= 0 "
            f"AND low >= 0 AND close >= 0);"
        )
        op.execute(sql)
        sql = (
            f"ALTER TABLE {table_name} ADD CONSTRAINT "
            f"chk_{table_name}_high_low_logic "
            f"CHECK (high >= low AND high >= open AND high >= close "
            f"AND low <= open AND low <= close);"
        )
        op.execute(sql)
        sql = (
            f"ALTER TABLE {table_name} ADD CONSTRAINT "
            f"chk_{table_name}_volume_non_negative "
            f"CHECK (volume >= 0);"
        )
        op.execute(sql)

    for n in (
        "stocks_1m",
        "stocks_5m",
        "stocks_15m",
        "stocks_30m",
        "stocks_1h",
    ):
        _create_intraday_sql(n)

    def _create_periodic_sql(table_name):
        op.create_table(
            table_name,
            sa.Column(
                "id", sa.Integer(), primary_key=True, autoincrement=True
            ),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("open", sa.Numeric(), nullable=False),
            sa.Column("high", sa.Numeric(), nullable=False),
            sa.Column("low", sa.Numeric(), nullable=False),
            sa.Column("close", sa.Numeric(), nullable=False),
            sa.Column(
                "volume", sa.BigInteger(), nullable=False, server_default="0"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=True,
                server_default=text("now()"),
            ),
            sa.ForeignKeyConstraint(
                ["symbol"], ["stock_master.stock_code"], ondelete="CASCADE"
            ),
        )
        op.create_unique_constraint(
            f"uq_{table_name}_symbol_date", table_name, ["symbol", "date"]
        )
        op.create_index(f"idx_{table_name}_symbol", table_name, ["symbol"])
        op.create_index(f"idx_{table_name}_date", table_name, ["date"])
        # symbol と date DESC の複合インデックス
        sql = (
            f"CREATE INDEX IF NOT EXISTS "
            f"idx_{table_name}_symbol_date_desc "
            f"ON {table_name} (symbol, date DESC);"
        )
        op.execute(sql)
        # 価格とボリュームに関する CHECK 制約
        sql = (
            f"ALTER TABLE {table_name} ADD CONSTRAINT "
            f"chk_{table_name}_non_negative_prices "
            f"CHECK (open >= 0 AND high >= 0 AND low >= 0 AND close >= 0);"
        )
        op.execute(sql)
        sql = (
            f"ALTER TABLE {table_name} ADD CONSTRAINT "
            f"chk_{table_name}_high_low_logic "
            f"CHECK (high >= low AND high >= open AND high >= close "
            f"AND low <= open AND low <= close);"
        )
        op.execute(sql)
        sql = (
            f"ALTER TABLE {table_name} ADD CONSTRAINT "
            f"chk_{table_name}_volume_non_negative "
            f"CHECK (volume >= 0);"
        )
        op.execute(sql)

    for n in ("stocks_1d", "stocks_1wk", "stocks_1mo"):
        _create_periodic_sql(n)


def downgrade() -> None:
    # 逆方向: 日次/週次/月次テーブルを削除
    for name in ("stocks_1mo", "stocks_1wk", "stocks_1d"):
        op.execute(f"DROP INDEX IF EXISTS idx_{name}_symbol_date_desc;")
        op.drop_index(f"idx_{name}_date", table_name=name)
        op.drop_index(f"idx_{name}_symbol", table_name=name)
        op.drop_constraint(f"uq_{name}_symbol_date", name, type_="unique")
        op.drop_table(name)

    # 逆方向: 分/時間足テーブルを削除
    for name in (
        "stocks_1h",
        "stocks_30m",
        "stocks_15m",
        "stocks_5m",
        "stocks_1m",
    ):
        op.execute(f"DROP INDEX IF EXISTS idx_{name}_symbol_datetime_desc;")
        op.drop_index(f"idx_{name}_datetime", table_name=name)
        op.drop_index(f"idx_{name}_symbol", table_name=name)
        op.drop_constraint(f"uq_{name}_symbol_datetime", name, type_="unique")
        op.drop_table(name)

    # バッチ実行詳細を削除
    op.drop_index(
        "idx_batch_execution_details_batch_stock",
        table_name="batch_execution_details",
    )
    op.drop_index(
        "idx_batch_execution_details_stock_code",
        table_name="batch_execution_details",
    )
    op.drop_index(
        "idx_batch_execution_details_status",
        table_name="batch_execution_details",
    )
    op.drop_index(
        "idx_batch_execution_details_batch_id",
        table_name="batch_execution_details",
    )
    op.drop_table("batch_execution_details")

    # バッチ実行サマリを削除
    op.drop_index(
        "idx_batch_executions_start_time", table_name="batch_executions"
    )
    op.drop_index(
        "idx_batch_executions_batch_type", table_name="batch_executions"
    )
    op.drop_index("idx_batch_executions_status", table_name="batch_executions")
    op.drop_table("batch_executions")

    # 銘柄マスタ更新履歴を削除
    op.drop_table("stock_master_updates")

    # 銘柄マスタを削除
    op.drop_index("idx_stock_master_sector_33", table_name="stock_master")
    op.drop_index("idx_stock_master_market", table_name="stock_master")
    op.drop_index("idx_stock_master_active", table_name="stock_master")
    op.drop_index("idx_stock_master_code", table_name="stock_master")
    op.drop_constraint(
        "uix_stock_master_stock_code", "stock_master", type_="unique"
    )
    op.drop_table("stock_master")
