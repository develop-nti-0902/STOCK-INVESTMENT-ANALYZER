"""`latest_stocks_1d` マテリアライズドビューを作成するマイグレーション

Revision ID: b7f3c1a2d9e4
Revises: a34daef60fc9
Create Date: 2026-01-22 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f3c1a2d9e4"
down_revision: Union[str, Sequence[str], None] = "a34daef60fc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """スキーマをアップグレードします：マテリアライズドビューとユニークインデックスを作成します。"""
    # 注意: マテリアライズドビューを作成し、`symbol` に対するユニークインデックスを作成します。
    # `REFRESH MATERIALIZED VIEW CONCURRENTLY` はトランザクション外で実行する必要があるため、
    # 本マイグレーションではリフレッシュ処理は行いません。
    op.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS latest_stocks_1d AS
        SELECT DISTINCT ON (symbol) *
        FROM stocks_1d
        ORDER BY symbol, timestamp DESC;
        """
    )
    op.execute(
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "uix_latest_stocks_1d_symbol ON latest_stocks_1d (symbol);"
        )
    )


def downgrade() -> None:
    """スキーマをダウングレードします：インデックスとマテリアライズドビューを削除します。"""
    op.execute("DROP INDEX IF EXISTS uix_latest_stocks_1d_symbol;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS latest_stocks_1d;")
