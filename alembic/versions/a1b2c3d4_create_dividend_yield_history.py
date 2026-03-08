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
down_revision: Union[str, Sequence[str], None] = "565383c201cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create dividend_yield_history table."""
    op.create_table(
        "dividend_yield_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=10), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "dividend",
            sa.Numeric(precision=20, scale=4),
            nullable=True,
            comment="年間配当金（COALESCE(dividend_adj, dividend_actual)）",
        ),
        sa.Column(
            "stock_price",
            sa.Numeric(precision=20, scale=4),
            nullable=True,
            comment="株価（COALESCE(adj_close, close)）",
        ),
        sa.Column(
            "dividend_yield",
            sa.Numeric(precision=8, scale=4),
            nullable=True,
            comment="配当利回り = dividend / stock_price",
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("edinet_document_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["edinet_document_id"],
            ["edinet_document.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", "date", name="uq_dividend_yield_history_symbol_date"),
    )

    # インデックス作成
    with op.batch_alter_table("dividend_yield_history", schema=None) as batch_op:
        batch_op.create_index(
            "idx_dividend_yield_history_date",
            ["date"],
            unique=False,
        )
        batch_op.create_index(
            "idx_dividend_yield_history_symbol_date",
            ["symbol", "date"],
            unique=False,
        )
        batch_op.create_index(
            "idx_dividend_yield_history_fiscal_year",
            ["fiscal_year"],
            unique=False,
        )
        batch_op.create_index(
            "idx_dividend_yield_history_edinet_document_id",
            ["edinet_document_id"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema: drop dividend_yield_history table."""
    op.drop_table("dividend_yield_history")
