"""refactor: evaluation_date -> evaluation_year in screening_results table

Revision ID: 8c3d4f5b6a7c
Revises: 7b959deaeb88
Create Date: 2026-03-03 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.sql import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "8c3d4f5b6a7c"
down_revision = "7b959deaeb88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """upgrade: evaluation_date (DATE) -> evaluation_year (INTEGER)"""

    connection = op.get_bind()
    db_dialect = str(connection.dialect).lower()

    # SQLiteはbatch_alter_tableを使用
    if "sqlite" in db_dialect:
        # Step 1: batch_alter_tableで evaluation_year を新規追加
        with op.batch_alter_table("screening_results", schema=None) as batch_op:
            batch_op.add_column(sa.Column("evaluation_year", sa.Integer(), nullable=True))
            # 古い制約を削除（batch内で処理）
            batch_op.drop_constraint("uq_screening_results_symbol_eval", type_="unique")
            # インデックス削除
            batch_op.drop_index("idx_screening_results_evaluation_date")

        # Step 2: データ変換実行（batch外で実行）
        connection.execute(
            text(
                """UPDATE screening_results
               SET evaluation_year = CAST(strftime('%Y', evaluation_date) AS INTEGER)
               WHERE evaluation_date IS NOT NULL"""
            )
        )

        # Step 3: 重複削除
        connection.execute(
            text(
                """DELETE FROM screening_results
               WHERE rowid NOT IN (
                   SELECT MAX(rowid)
                   FROM screening_results
                   GROUP BY symbol, evaluation_year
               )"""
            )
        )

        # Step 4: batch_alter_tableで evaluation_date を削除し、新しい制約・インデックスを追加
        with op.batch_alter_table("screening_results", schema=None) as batch_op:
            # evaluation_year を NOT NULL に変更
            batch_op.alter_column("evaluation_year", existing_type=sa.Integer(), nullable=False)
            # 古い evaluation_date カラムを削除
            batch_op.drop_column("evaluation_date")
            # 新しい一意制約を追加
            batch_op.create_unique_constraint(
                "uq_screening_results_symbol_year", ["symbol", "evaluation_year"]
            )
            # 新しいインデックスを追加
            batch_op.create_index("idx_screening_results_evaluation_year", ["evaluation_year"])
    else:
        # MariaDB / MySQL版
        op.add_column(
            "screening_results", sa.Column("evaluation_year", sa.Integer(), nullable=True)
        )

        connection.execute(
            text(
                """UPDATE screening_results
               SET evaluation_year = EXTRACT(YEAR FROM evaluation_date)
               WHERE evaluation_date IS NOT NULL"""
            )
        )

        connection.execute(
            text(
                """DELETE FROM screening_results sr1
               WHERE sr1.id NOT IN (
                   SELECT MAX(sr2.id)
                   FROM screening_results sr2
                   GROUP BY sr2.symbol, sr2.evaluation_year
               )"""
            )
        )

        op.alter_column(
            "screening_results", "evaluation_year", existing_type=sa.Integer(), nullable=False
        )

        op.drop_constraint("uq_screening_results_symbol_eval", "screening_results", type_="unique")

        op.create_unique_constraint(
            "uq_screening_results_symbol_year", "screening_results", ["symbol", "evaluation_year"]
        )

        op.drop_index("idx_screening_results_evaluation_date", "screening_results")
        op.create_index(
            "idx_screening_results_evaluation_year", "screening_results", ["evaluation_year"]
        )

        op.drop_column("screening_results", "evaluation_date")


def downgrade() -> None:
    """downgrade: evaluation_year -> evaluation_date"""

    connection = op.get_bind()
    db_dialect = str(connection.dialect).lower()

    if "sqlite" in db_dialect:
        with op.batch_alter_table("screening_results", schema=None) as batch_op:
            # 新カラム追加
            batch_op.add_column(sa.Column("evaluation_date", sa.Date(), nullable=True))

        # ダミー値設定
        connection.execute(
            text(
                """UPDATE screening_results
               SET evaluation_date = date(evaluation_year || '-04-01')
               WHERE evaluation_year IS NOT NULL"""
            )
        )

        with op.batch_alter_table("screening_results", schema=None) as batch_op:
            # NOT NULL に変更
            batch_op.alter_column("evaluation_date", existing_type=sa.Date(), nullable=False)

            # evaluation_year カラムを削除
            batch_op.drop_column("evaluation_year")

            # 制約を復元
            batch_op.drop_constraint("uq_screening_results_symbol_year", type_="unique")
            batch_op.create_unique_constraint(
                "uq_screening_results_symbol_eval", ["symbol", "evaluation_date"]
            )
    else:
        op.add_column("screening_results", sa.Column("evaluation_date", sa.Date(), nullable=True))

        connection.execute(
            text(
                """UPDATE screening_results
               SET evaluation_date = STR_TO_DATE(CONCAT(evaluation_year, '-04-01'), '%Y-%m-%d')
               WHERE evaluation_year IS NOT NULL"""
            )
        )

        op.alter_column(
            "screening_results", "evaluation_date", existing_type=sa.Date(), nullable=False
        )

        op.drop_constraint("uq_screening_results_symbol_year", "screening_results", type_="unique")

        op.create_unique_constraint(
            "uq_screening_results_symbol_eval", "screening_results", ["symbol", "evaluation_date"]
        )

        op.drop_index("idx_screening_results_evaluation_year", "screening_results")
        op.create_index(
            "idx_screening_results_evaluation_date", "screening_results", ["evaluation_date"]
        )

        op.drop_column("screening_results", "evaluation_year")
