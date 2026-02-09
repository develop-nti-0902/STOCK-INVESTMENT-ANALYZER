"""`latest_stocks_1d` マテリアライズドビューを作成するマイグレーション.

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
    """スキーマをアップグレードします：マテリアライズドビューとユニークインデックスを作成します."""
    # 注意: マテリアライズドビューを作成し、`symbol` に対するユニークインデックスを作成します。
    # `REFRESH MATERIALIZED VIEW CONCURRENTLY` はトランザクション外で実行する必要があるため、
    # 本マイグレーションではリフレッシュ処理は行いません。
    # SQLite では MATERIALIZED VIEW と DISTINCT ON をサポートしないため、
    # 各銘柄ごとに最新の timestamp をサブクエリで取得し、それに JOIN する
    # 形で VIEW を定義します。
    op.execute(
        """
        CREATE VIEW IF NOT EXISTS latest_stocks_1d AS
        SELECT s.*
        FROM stocks_1d AS s
        JOIN (
            SELECT symbol, MAX(timestamp) AS max_ts
            FROM stocks_1d
            GROUP BY symbol
        ) AS t
        ON s.symbol = t.symbol AND s.timestamp = t.max_ts;
        """
    )


def downgrade() -> None:
    """スキーマをダウングレードします：VIEW を削除します."""
    # VIEW を削除
    op.execute("DROP VIEW IF EXISTS latest_stocks_1d;")
