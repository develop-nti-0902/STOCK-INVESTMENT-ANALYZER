"""Add edinet_balance_sheet (initial - NOOP placeholder)

Revision ID: c1d2e3f4g5h6
Revises: 565383c201cb
Create Date: 2026-02-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

revision: str = "c1d2e3f4g5h6"
down_revision: Union[str, Sequence[str], None] = "565383c201cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
