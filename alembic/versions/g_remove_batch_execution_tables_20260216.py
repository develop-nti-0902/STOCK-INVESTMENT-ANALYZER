"""drop batch execution tables

Revision ID: g_remove_batch_execution_tables_20260216
Revises: f1a2b3c4d5e6
Create Date: 2026-02-16 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "g_remove_batch_execution_tables_20260216"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    try:
        # Try to drop details first because of FK
        op.execute("DROP TABLE IF EXISTS batch_execution_details")
    except Exception:
        try:
            # best-effort: ignore if not exists
            pass
        except Exception:
            pass

    try:
        op.execute("DROP TABLE IF EXISTS batch_executions")
    except Exception:
        pass


def downgrade() -> None:
    # Downgrade not supported for destructive removal.
    pass
