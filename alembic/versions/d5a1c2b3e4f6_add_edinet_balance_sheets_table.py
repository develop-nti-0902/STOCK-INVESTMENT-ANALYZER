"""add edinet_balance_sheets table

Revision ID: d5a1c2b3e4f6
Revises: c1f9d2b3e4f5
Create Date: 2026-01-31 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5a1c2b3e4f6"
down_revision: Union[str, Sequence[str], None] = "c1f9d2b3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: create edinet_balance_sheets table."""
    op.create_table(
        "edinet_balance_sheets",
        sa.Column("doc_id", sa.String(length=50), nullable=False),
        sa.Column("sec_code", sa.String(length=10), nullable=False),
        sa.Column("filer_name", sa.String(length=255), nullable=True),
        sa.Column("submission_date", sa.Date(), nullable=False),
        sa.Column("period_end_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column(
            "report_type",
            sa.String(length=20),
            nullable=False,
            server_default="annual",
        ),
        sa.Column("total_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("non_current_assets", sa.Numeric(20, 2), nullable=True),
        sa.Column("cash_and_equivalents", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("current_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("non_current_liabilities", sa.Numeric(20, 2), nullable=True),
        sa.Column("short_term_loans", sa.Numeric(20, 2), nullable=True),
        sa.Column("long_term_loans", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_equity", sa.Numeric(20, 2), nullable=True),
        sa.Column("shareholders_equity", sa.Numeric(20, 2), nullable=True),
        sa.Column("retained_earnings", sa.Numeric(20, 2), nullable=True),
        sa.Column("bps", sa.Numeric(10, 2), nullable=True),
        sa.Column("equity_to_asset_ratio", sa.Numeric(5, 2), nullable=True),
        sa.Column("candidate_contexts", sa.String(length=50), nullable=True),
        sa.Column("candidate_keys", sa.String(length=50), nullable=True),
        sa.Column("is_consolidated", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sec_code", "period_end_date", name="uq_edinet_sec_period"
        ),
    )
    op.create_index(
        "idx_edinet_balance_doc_id",
        "edinet_balance_sheets",
        ["doc_id"],
        unique=False,
    )
    op.create_index(
        "idx_edinet_balance_sec_code_period",
        "edinet_balance_sheets",
        ["sec_code", "period_end_date"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema: drop edinet_balance_sheets table."""
    op.drop_index(
        "idx_edinet_balance_sec_code_period",
        table_name="edinet_balance_sheets",
    )
    op.drop_index(
        "idx_edinet_balance_doc_id", table_name="edinet_balance_sheets"
    )
    op.drop_table("edinet_balance_sheets")
