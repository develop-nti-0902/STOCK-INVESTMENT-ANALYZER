"""Add latest_stocks_1d view

Revision ID: 8c6b6b094d99
Revises: 67bd98bae213
Create Date: 2026-03-15 21:12:26.342064

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c6b6b094d99"
down_revision: Union[str, Sequence[str], None] = "67bd98bae213"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create latest_stocks_1d view
    # This view returns the latest record for each symbol
    op.execute(
        """
        CREATE VIEW latest_stocks_1d AS
        SELECT
            id,
            symbol,
            timestamp,
            open,
            high,
            low,
            close,
            adj_close,
            volume,
            created_at,
            updated_at
        FROM stocks_1d
        WHERE (symbol, timestamp) IN (
            SELECT symbol, MAX(timestamp)
            FROM stocks_1d
            GROUP BY symbol
        )
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop latest_stocks_1d view
    op.execute("DROP VIEW IF EXISTS latest_stocks_1d")
