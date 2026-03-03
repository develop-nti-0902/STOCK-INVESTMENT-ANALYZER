"""Create latest_stocks materialized views

Revision ID: 8d0e4f5c6b9a
Revises: 8c3d4f5b6a7c
Create Date: 2026-03-03 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8d0e4f5c6b9a"
down_revision: Union[str, Sequence[str], None] = "8c3d4f5b6a7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create latest_stocks views for each timeframe."""
    # latest_stocks_1d: 日足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_1d AS
        SELECT *
        FROM stocks_1d s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_1d
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_1h: 1時間足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_1h AS
        SELECT *
        FROM stocks_1h s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_1h
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_5m: 5分足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_5m AS
        SELECT *
        FROM stocks_5m s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_5m
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_15m: 15分足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_15m AS
        SELECT *
        FROM stocks_15m s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_15m
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_30m: 30分足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_30m AS
        SELECT *
        FROM stocks_30m s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_30m
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_1m: 1分足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_1m AS
        SELECT *
        FROM stocks_1m s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_1m
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_1wk: 週足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_1wk AS
        SELECT *
        FROM stocks_1wk s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_1wk
            WHERE symbol = s.symbol
        )
        """
    )

    # latest_stocks_1mo: 月足の最新レコードビュー
    op.execute(
        """
        CREATE VIEW latest_stocks_1mo AS
        SELECT *
        FROM stocks_1mo s
        WHERE s.timestamp = (
            SELECT MAX(timestamp)
            FROM stocks_1mo
            WHERE symbol = s.symbol
        )
        """
    )


def downgrade() -> None:
    """Drop latest_stocks views."""
    op.execute("DROP VIEW IF EXISTS latest_stocks_1mo")
    op.execute("DROP VIEW IF EXISTS latest_stocks_1wk")
    op.execute("DROP VIEW IF EXISTS latest_stocks_1m")
    op.execute("DROP VIEW IF EXISTS latest_stocks_30m")
    op.execute("DROP VIEW IF EXISTS latest_stocks_15m")
    op.execute("DROP VIEW IF EXISTS latest_stocks_5m")
    op.execute("DROP VIEW IF EXISTS latest_stocks_1h")
    op.execute("DROP VIEW IF EXISTS latest_stocks_1d")
