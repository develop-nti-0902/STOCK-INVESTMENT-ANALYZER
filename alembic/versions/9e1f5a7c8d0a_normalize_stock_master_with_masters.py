"""Normalize stock_master with master tables for sector/market/scale

Revision ID: 9e1f5a7c8d0a
Revises: 8d0e4f5c6b9a
Create Date: 2026-02-26 20:00:00.000000

Description:
    Creates 4 new master tables:
    - market_category_master (market categories: Prime/Standard/Growth)
    - sector_33_master (33-class industry classification)
    - sector_17_master (17-class industry classification)
    - scale_master (company scale: L/M/S)

    Modifies stock_master to use FK references instead of denormalized columns.
    Supports both SQLite and PostgreSQL via batch_alter_table.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e1f5a7c8d0a"
down_revision: Union[str, Sequence[str], None] = "8d0e4f5c6b9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create master tables and normalize stock_master."""

    # Step 1: Create market_category_master
    op.create_table(
        "market_category_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_market_category_master_code", "code"),
    )

    # Step 2: Create sector_33_master
    op.create_table(
        "sector_33_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_sector_33_master_code", "code"),
    )

    # Step 3: Create sector_17_master
    op.create_table(
        "sector_17_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_sector_17_master_code", "code"),
    )

    # Step 4: Create scale_master
    op.create_table(
        "scale_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_scale_master_code", "code"),
    )

    # Step 5-7: Use batch_operations for SQLite compatibility
    with op.batch_alter_table("stock_master", schema=None) as batch_op:
        # Add FK columns
        batch_op.add_column(
            sa.Column(
                "market_category_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "sector_33_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "sector_17_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "scale_id",
                sa.Integer(),
                nullable=True,
            )
        )

        # Add indexes for FK columns
        batch_op.create_index(
            "idx_stock_master_market_category_id",
            ["market_category_id"],
        )
        batch_op.create_index(
            "idx_stock_master_sector_33_id",
            ["sector_33_id"],
        )
        batch_op.create_index(
            "idx_stock_master_sector_17_id",
            ["sector_17_id"],
        )
        batch_op.create_index(
            "idx_stock_master_scale_id",
            ["scale_id"],
        )

        # Drop denormalized columns
        batch_op.drop_column("sector_name_33")
        batch_op.drop_column("sector_name_17")
        batch_op.drop_column("scale_category")


def downgrade() -> None:
    """Revert normalization - restore denormalized columns and remove master tables."""

    # Step 1-3: Use batch_operations for SQLite compatibility
    with op.batch_alter_table("stock_master", schema=None) as batch_op:
        # Re-add denormalized columns
        batch_op.add_column(sa.Column("sector_name_33", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("sector_name_17", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("scale_category", sa.String(10), nullable=True))

        # Drop indexes
        batch_op.drop_index("idx_stock_master_market_category_id")
        batch_op.drop_index("idx_stock_master_sector_33_id")
        batch_op.drop_index("idx_stock_master_sector_17_id")
        batch_op.drop_index("idx_stock_master_scale_id")

        # Drop FK columns
        batch_op.drop_column("market_category_id")
        batch_op.drop_column("sector_33_id")
        batch_op.drop_column("sector_17_id")
        batch_op.drop_column("scale_id")

    # Step 4: Drop master tables
    op.drop_table("scale_master")
    op.drop_table("sector_17_master")
    op.drop_table("sector_33_master")
    op.drop_table("market_category_master")
