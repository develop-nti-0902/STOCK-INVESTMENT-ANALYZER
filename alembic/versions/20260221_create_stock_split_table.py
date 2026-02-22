"""create stock_split table

Revision ID: 20260221_create_stock_split_table
Revises: add_edinet_sd_dividend_adj_20260221
Create Date: 2026-02-21 00:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260221_create_stock_split_table"
down_revision: Union[str, Sequence[str], None] = "add_edinet_sd_dividend_adj_20260221"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("stock_split"):
        op.create_table(
            "stock_split",
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("effective_date", sa.Date(), nullable=False),
            sa.Column("ratio_from", sa.Integer(), nullable=True),
            sa.Column("ratio_to", sa.Integer(), nullable=True),
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
            sa.PrimaryKeyConstraint("id"),
        )

        with op.batch_alter_table("stock_split", schema=None) as batch_op:
            batch_op.create_index("idx_stock_split_code", ["code"], unique=False)
            batch_op.create_index("idx_stock_split_effective", ["effective_date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("stock_split"):
        with op.batch_alter_table("stock_split", schema=None) as batch_op:
            try:
                batch_op.drop_index("idx_stock_split_effective")
            except Exception:
                pass
            try:
                batch_op.drop_index("idx_stock_split_code")
            except Exception:
                pass
        op.drop_table("stock_split")
