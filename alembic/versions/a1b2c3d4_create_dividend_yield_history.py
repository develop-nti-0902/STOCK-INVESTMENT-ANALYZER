"""Create dividend_yield_history table.

Revision ID: a1b2c3d4
Revises: 565383c201cb
Create Date: 2026-03-07 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create dividend_yield_history table."""
    # Check if table already exists
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dividend_yield_history (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(10) NOT NULL,
            date DATE NOT NULL,
            dividend NUMERIC(20, 4),
            stock_price NUMERIC(20, 4),
            dividend_yield NUMERIC(8, 4),
            fiscal_year INTEGER NOT NULL,
            edinet_document_id INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (symbol, date),
            FOREIGN KEY (edinet_document_id) REFERENCES edinet_document(id)
        )
    """
    )

    # インデックス作成（既に存在する場合はスキップ）
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dividend_yield_history_date ON dividend_yield_history (date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dividend_yield_history_symbol_date ON dividend_yield_history (symbol, date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dividend_yield_history_fiscal_year ON dividend_yield_history (fiscal_year)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_dividend_yield_history_edinet_document_id ON dividend_yield_history (edinet_document_id)"
    )


def downgrade() -> None:
    """Downgrade schema: drop dividend_yield_history table."""
    op.drop_table("dividend_yield_history")
