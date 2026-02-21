"""create dividend_yield_monitoring table

Revision ID: i2a3b4c5d6e7
Revises: h1a2b3c4d5e6
Create Date: 2026-02-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i2a3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "h1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by creating dividend_yield_monitoring."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("dividend_yield_monitoring"):
        op.create_table(
            "dividend_yield_monitoring",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("sec_code", sa.String(length=10), nullable=False),
            sa.Column("monitoring_date", sa.Date(), nullable=False),
            sa.Column(
                "latest_dividend_amount",
                sa.Numeric(precision=20, scale=4),
                nullable=True,
            ),
            sa.Column(
                "latest_stock_price",
                sa.Numeric(precision=20, scale=4),
                nullable=True,
            ),
            sa.Column(
                "dividend_yield",
                sa.Numeric(precision=8, scale=4),
                nullable=True,
            ),
            sa.Column("purchase_level", sa.String(length=20), nullable=True),
            sa.Column("screening_status", sa.String(length=20), nullable=True),
            sa.Column("screening_total_score", sa.Integer(), nullable=True),
            sa.Column("stock_price_source_date", sa.Date(), nullable=True),
            sa.Column("dividend_source_date", sa.Date(), nullable=True),
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
                "monitoring_date",
                name="uq_dividend_yield_monitoring",
            ),
        )

        with op.batch_alter_table("dividend_yield_monitoring", schema=None) as batch_op:
            batch_op.create_index(
                "idx_dividend_yield_monitoring_date",
                ["monitoring_date"],
                unique=False,
            )
            batch_op.create_index(
                "idx_dividend_yield_monitoring_purchase_level",
                ["purchase_level"],
                unique=False,
            )
            batch_op.create_index(
                "idx_dividend_yield_monitoring_yield",
                ["dividend_yield"],
                unique=False,
            )


def downgrade() -> None:
    """Downgrade schema by dropping dividend_yield_monitoring."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("dividend_yield_monitoring"):
        with op.batch_alter_table("dividend_yield_monitoring", schema=None) as batch_op:
            try:
                batch_op.drop_index("idx_dividend_yield_monitoring_yield")
            except Exception:
                pass
            try:
                batch_op.drop_index("idx_dividend_yield_monitoring_purchase_level")
            except Exception:
                pass
            try:
                batch_op.drop_index("idx_dividend_yield_monitoring_date")
            except Exception:
                pass
        op.drop_table("dividend_yield_monitoring")
