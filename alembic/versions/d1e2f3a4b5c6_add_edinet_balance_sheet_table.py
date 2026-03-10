"""Rename edinet_balance_sheet columns: net_assets_per_share->bps, equity_to_asset_ratio->equity_ratio

Revision ID: d1e2f3a4b5c6
Revises: c1d2e3f4g5h6
Create Date: 2026-03-10 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4g5h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename edinet_balance_sheet columns."""
    with op.batch_alter_table("edinet_balance_sheet", schema=None) as batch_op:
        batch_op.alter_column(
            "net_assets_per_share",
            new_column_name="bps",
            existing_type=sa.Numeric(20, 2),
            nullable=True,
        )
        batch_op.alter_column(
            "equity_to_asset_ratio",
            new_column_name="equity_ratio",
            existing_type=sa.Numeric(20, 2),
            type_=sa.Numeric(20, 6),
            nullable=True,
        )


def downgrade() -> None:
    """Revert column renames."""
    with op.batch_alter_table("edinet_balance_sheet", schema=None) as batch_op:
        batch_op.alter_column(
            "equity_ratio",
            new_column_name="equity_to_asset_ratio",
            existing_type=sa.Numeric(20, 6),
            type_=sa.Numeric(20, 2),
            nullable=True,
        )
        batch_op.alter_column(
            "bps",
            new_column_name="net_assets_per_share",
            existing_type=sa.Numeric(20, 2),
            nullable=True,
        )
