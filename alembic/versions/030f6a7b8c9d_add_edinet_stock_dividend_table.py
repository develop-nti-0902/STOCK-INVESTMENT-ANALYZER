"""add edinet_stock_dividend table.

Revision ID: 030f6a7b8c9d
Revises: 020f5df7040c
Create Date: 2026-02-13 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "030f6a7b8c9d"
down_revision: Union[str, Sequence[str], None] = "020f5df7040c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("edinet_stock_dividend"):
        op.create_table(
            "edinet_stock_dividend",
            sa.Column("doc_id", sa.String(length=50), nullable=False),
            sa.Column("sec_code", sa.String(length=10), nullable=False),
            sa.Column("submission_date", sa.Date(), nullable=False),
            sa.Column("period_end_date", sa.Date(), nullable=False),
            sa.Column("fiscal_year", sa.Integer(), nullable=True),
            sa.Column("report_type", sa.String(length=20), nullable=False),
            sa.Column(
                "dividend_actual",
                sa.Numeric(precision=20, scale=2),
                nullable=True,
                comment="年間配当金",
            ),
            sa.Column("candidate_contexts", sa.String(length=50), nullable=True),
            sa.Column("candidate_keys", sa.String(length=50), nullable=True),
            sa.Column("is_consolidated", sa.Boolean(), nullable=True),
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
            sa.UniqueConstraint("sec_code", "period_end_date", name="uq_edinet_sd_sec_period"),
        )

        with op.batch_alter_table("edinet_stock_dividend", schema=None) as batch_op:
            batch_op.create_index("idx_edinet_sd_doc_id", ["doc_id"], unique=False)
            batch_op.create_index("idx_edinet_sd_period_end", ["period_end_date"], unique=False)
            batch_op.create_index("idx_edinet_sd_sec_code", ["sec_code"], unique=False)
            batch_op.create_index(
                "idx_edinet_sd_sec_period", ["sec_code", "period_end_date"], unique=False
            )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("edinet_stock_dividend"):
        with op.batch_alter_table("edinet_stock_dividend", schema=None) as batch_op:
            try:
                batch_op.drop_index("idx_edinet_sd_sec_period")
            except Exception:
                pass
            try:
                batch_op.drop_index("idx_edinet_sd_sec_code")
            except Exception:
                pass
            try:
                batch_op.drop_index("idx_edinet_sd_period_end")
            except Exception:
                pass
            try:
                batch_op.drop_index("idx_edinet_sd_doc_id")
            except Exception:
                pass

        op.drop_table("edinet_stock_dividend")
