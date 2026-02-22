"""add dividend_adj column to edinet_stock_dividend

Revision ID: add_edinet_sd_dividend_adj_20260221
Revises: g_remove_batch_execution_tables_20260216
Create Date: 2026-02-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_edinet_sd_dividend_adj_20260221"
down_revision: Union[str, Sequence[str], None] = "g_remove_batch_execution_tables_20260216"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add `dividend_adj` column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("edinet_stock_dividend"):
        with op.batch_alter_table("edinet_stock_dividend", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "dividend_adj",
                    sa.Numeric(precision=20, scale=2),
                    nullable=True,
                    comment="調整後年間配当金",
                )
            )


def downgrade() -> None:
    """Downgrade schema: remove `dividend_adj` column."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("edinet_stock_dividend"):
        with op.batch_alter_table("edinet_stock_dividend", schema=None) as batch_op:
            try:
                batch_op.drop_column("dividend_adj")
            except Exception:
                pass
