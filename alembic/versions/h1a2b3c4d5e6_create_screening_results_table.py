"""create screening_results table

Revision ID: h1a2b3c4d5e6
Revises: g_remove_batch_execution_tables_20260216
Create Date: 2026-02-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "g_remove_batch_execution_tables_20260216"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by creating screening_results table."""
    op.create_table(
        "screening_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sec_code", sa.String(length=10), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("fiscal_year_end", sa.Date(), nullable=True),
        sa.Column(
            "pass_required_conditions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("score_dividend", sa.Integer(), nullable=True),
        sa.Column("score_eps", sa.Integer(), nullable=True),
        sa.Column("score_stability", sa.Integer(), nullable=True),
        sa.Column("score_profitability", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'not_eligible'"),
        ),
        sa.Column("failed_conditions", sa.JSON(), nullable=True),
        sa.Column("screening_details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "sec_code",
            "evaluation_date",
            name="uq_screening_results_sec_eval",
        ),
    )
    op.create_index(
        "idx_screening_results_sec_code",
        "screening_results",
        ["sec_code"],
        unique=False,
    )
    op.create_index(
        "idx_screening_results_evaluation_date",
        "screening_results",
        ["evaluation_date"],
        unique=False,
    )
    op.create_index(
        "idx_screening_results_status",
        "screening_results",
        ["status"],
        unique=False,
    )
    op.create_index(
        "idx_screening_results_total_score",
        "screening_results",
        ["total_score"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema by dropping screening_results table."""
    op.drop_index("idx_screening_results_status", table_name="screening_results")
    op.drop_index(
        "idx_screening_results_evaluation_date",
        table_name="screening_results",
    )
    op.drop_index("idx_screening_results_total_score", table_name="screening_results")
    op.drop_index("idx_screening_results_sec_code", table_name="screening_results")
    op.drop_table("screening_results")
