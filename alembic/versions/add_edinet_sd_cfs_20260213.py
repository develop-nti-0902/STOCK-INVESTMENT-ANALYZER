"""add edinet stock_dividend and cash_flow_statement tables.

Revision ID: add_edinet_sd_cfs_20260213
Revises: db11330dca45
Create Date: 2026-02-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_edinet_sd_cfs_20260213"
down_revision: Union[str, Sequence[str], None] = "db11330dca45"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create EDINET stock_dividend and cash_flow_statement tables."""
    op.create_table(
        "edinet_stock_dividend",
        sa.Column("doc_id", sa.VARCHAR(length=50), nullable=False),
        sa.Column("sec_code", sa.VARCHAR(length=10), nullable=False),
        sa.Column("submission_date", sa.DATE(), nullable=False),
        sa.Column("period_end_date", sa.DATE(), nullable=False),
        sa.Column("fiscal_year", sa.INTEGER(), nullable=True),
        sa.Column("report_type", sa.VARCHAR(length=20), nullable=False),
        sa.Column("dividend_actual", sa.NUMERIC(precision=20, scale=2), nullable=True),
        sa.Column("candidate_contexts", sa.VARCHAR(length=50), nullable=True),
        sa.Column("candidate_keys", sa.VARCHAR(length=50), nullable=True),
        sa.Column("is_consolidated", sa.BOOLEAN(), nullable=True),
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sec_code", "period_end_date", name=op.f("uq_edinet_sd_sec_period")),
    )

    with op.batch_alter_table("edinet_stock_dividend", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("idx_edinet_sd_sec_period"), ["sec_code", "period_end_date"], unique=False
        )
        batch_op.create_index(batch_op.f("idx_edinet_sd_sec_code"), ["sec_code"], unique=False)
        batch_op.create_index(
            batch_op.f("idx_edinet_sd_period_end"), ["period_end_date"], unique=False
        )
        batch_op.create_index(batch_op.f("idx_edinet_sd_doc_id"), ["doc_id"], unique=False)

    op.create_table(
        "edinet_cash_flow_statement",
        sa.Column("doc_id", sa.VARCHAR(length=50), nullable=False),
        sa.Column("sec_code", sa.VARCHAR(length=10), nullable=False),
        sa.Column("submission_date", sa.DATE(), nullable=False),
        sa.Column("period_end_date", sa.DATE(), nullable=False),
        sa.Column("fiscal_year", sa.INTEGER(), nullable=True),
        sa.Column("report_type", sa.VARCHAR(length=20), nullable=False),
        sa.Column("operating_cf", sa.NUMERIC(precision=20, scale=2), nullable=True),
        sa.Column("candidate_contexts", sa.VARCHAR(length=50), nullable=True),
        sa.Column("candidate_keys", sa.VARCHAR(length=50), nullable=True),
        sa.Column("is_consolidated", sa.BOOLEAN(), nullable=True),
        sa.Column("id", sa.INTEGER(), nullable=False),
        sa.Column(
            "created_at",
            sa.DATETIME(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DATETIME(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sec_code", "period_end_date", name=op.f("uq_edinet_cfs_sec_period")),
    )

    with op.batch_alter_table("edinet_cash_flow_statement", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("idx_edinet_cfs_sec_period"), ["sec_code", "period_end_date"], unique=False
        )
        batch_op.create_index(batch_op.f("idx_edinet_cfs_sec_code"), ["sec_code"], unique=False)
        batch_op.create_index(
            batch_op.f("idx_edinet_cfs_period_end"), ["period_end_date"], unique=False
        )
        batch_op.create_index(batch_op.f("idx_edinet_cfs_doc_id"), ["doc_id"], unique=False)


def downgrade() -> None:
    """Drop EDINET stock_dividend and cash_flow_statement tables."""
    with op.batch_alter_table("edinet_cash_flow_statement", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("idx_edinet_cfs_doc_id"))
        batch_op.drop_index(batch_op.f("idx_edinet_cfs_period_end"))
        batch_op.drop_index(batch_op.f("idx_edinet_cfs_sec_code"))
        batch_op.drop_index(batch_op.f("idx_edinet_cfs_sec_period"))

    op.drop_table("edinet_cash_flow_statement")

    with op.batch_alter_table("edinet_stock_dividend", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("idx_edinet_sd_doc_id"))
        batch_op.drop_index(batch_op.f("idx_edinet_sd_period_end"))
        batch_op.drop_index(batch_op.f("idx_edinet_sd_sec_code"))
        batch_op.drop_index(batch_op.f("idx_edinet_sd_sec_period"))

    op.drop_table("edinet_stock_dividend")
