"""merge heads for edinet profit and loss.

Revision ID: 086c83420b27
Revises: d2f4e6a7b8c9, f1a2b3c4d5e6
Create Date: 2026-02-11 09:08:53.897270

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "086c83420b27"
down_revision: Union[str, Sequence[str], None] = ("d2f4e6a7b8c9", "f1a2b3c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
