"""merge multiple heads

Revision ID: 021efaad97b1
Revises: 20260221_create_stock_split_table, add_edinet_sd_cfs_20260213, i2a3b4c5d6e7
Create Date: 2026-02-26 18:46:36.438991

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "021efaad97b1"
down_revision: Union[str, Sequence[str], None] = (
    "20260221_create_stock_split_table",
    "add_edinet_sd_cfs_20260213",
    "i2a3b4c5d6e7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
