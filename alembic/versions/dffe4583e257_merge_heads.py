"""merge heads

Revision ID: dffe4583e257
Revises: 030f6a7b8c9d, 30cfae9b1a2b
Create Date: 2026-02-13 19:40:42.802199

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dffe4583e257"
down_revision: Union[str, Sequence[str], None] = ("030f6a7b8c9d", "30cfae9b1a2b")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
