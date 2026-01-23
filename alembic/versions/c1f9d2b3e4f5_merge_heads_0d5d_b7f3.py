"""merge heads: 0d5d2098df45, b7f3c1a2d9e4

このマイグレーションは複数の head を統合するためのマージコミットです。
実際のスキーマ変更は含まず、 Alembic の履歴を一本化するために使用します。

Revision ID: c1f9d2b3e4f5
Revises: (0d5d2098df45, b7f3c1a2d9e4)
Create Date: 2026-01-22 10:30:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c1f9d2b3e4f5"
down_revision: Union[str, Sequence[str], None] = (
    "0d5d2098df45",
    "b7f3c1a2d9e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """ヘッド統合用の空アップグレード（変更なし）。"""
    pass


def downgrade() -> None:
    """ヘッド統合を元に戻す操作は定義していません（非可逆）。"""
    pass
