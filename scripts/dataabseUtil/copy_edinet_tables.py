"""
EDINETテーブルのスキーマ変換コピー処理

機能:
- ソースDBのEDINETテーブル（edinet_cash_flow_statement, edinet_profit_and_loss, edinet_stock_dividend）
  から宛先DBへスキーマ変換してコピー
- 宛先DBの中間テーブル（edinet_document）を構築し、外部キー制約に対応
- トランザクション処理とログ出力

使用例:
    poetry run python scripts/dataabseUtil/copy_edinet_tables.py
    poetry run python scripts/dataabseUtil/copy_edinet_tables.py --src F:/path/to/source.db --dest F:/path/to/dest.db
"""

import argparse
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class EDINETTableCopier:
    """EDINETテーブルをソースから宛先にコピーするクラス"""

    def __init__(self, src_db_path: str, dest_db_path: str):
        """
        初期化

        Args:
            src_db_path: ソースDB のパス
            dest_db_path: 宛先DB のパス
        """
        self.src_db_path = src_db_path
        self.dest_db_path = dest_db_path
        self.src_conn = None
        self.dest_conn = None
        self.doc_id_mapping = {}  # {doc_id: edinet_document_id}

    def connect(self) -> None:
        """DBに接続"""
        try:
            self.src_conn = sqlite3.connect(self.src_db_path)
            self.src_conn.row_factory = sqlite3.Row
            self.dest_conn = sqlite3.connect(self.dest_db_path)
            self.dest_conn.row_factory = sqlite3.Row
            logger.info(f"ソースDB接続: {self.src_db_path}")
            logger.info(f"宛先DB接続: {self.dest_db_path}")
        except sqlite3.Error as e:
            logger.error(f"DB接続エラー: {e}")
            raise

    def close(self) -> None:
        """DB接続を閉じる"""
        if self.src_conn:
            self.src_conn.close()
        if self.dest_conn:
            self.dest_conn.close()
        logger.info("DB接続を閉じました")

    def get_table_count(self, conn: sqlite3.Connection, table_name: str) -> int:
        """テーブルの行数を取得"""
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.warning(f"行数取得エラー ({table_name}): {e}")
            return 0

    def step1_cleanup_dest_tables(self) -> None:
        """
        STEP 1: 宛先DBのテーブルをクリーンアップ
        FK制約の削除順: cash_flow → profit_and_loss → stock_dividend → document
        """
        logger.info("=" * 60)
        logger.info("STEP 1: 宛先DBのテーブルをクリーンアップ")
        logger.info("=" * 60)

        try:
            cursor = self.dest_conn.cursor()

            # FK制約を一時的に無効化
            cursor.execute("PRAGMA foreign_keys = OFF")

            tables_to_delete = [
                "edinet_cash_flow_statement",
                "edinet_profit_and_loss",
                "edinet_stock_dividend",
                "edinet_document",
            ]

            for table_name in tables_to_delete:
                before_count = self.get_table_count(self.dest_conn, table_name)
                cursor.execute(f"DELETE FROM {table_name}")
                after_count = self.get_table_count(self.dest_conn, table_name)
                logger.info(f"{table_name}: {before_count} → {after_count} 行")

            self.dest_conn.commit()
            logger.info("クリーンアップ完了")

        except sqlite3.Error as e:
            logger.error(f"クリーンアップ中のエラー: {e}")
            self.dest_conn.rollback()
            raise

    def step2_build_edinet_document(self) -> None:
        """
        STEP 2: edinet_document テーブルを構築
        ソースの3テーブルから doc_id, sec_code, submission_date, report_type,
        candidate_contexts, candidate_keys を集約する
        """
        logger.info("=" * 60)
        logger.info("STEP 2: edinet_document テーブルを構築")
        logger.info("=" * 60)

        try:
            cursor = self.dest_conn.cursor()

            # UNION クエリでソースの3テーブルから抽出
            union_query = """
            SELECT
                doc_id,
                sec_code,
                submission_date,
                report_type,
                candidate_contexts,
                candidate_keys
            FROM (
                SELECT
                    doc_id, sec_code, submission_date, report_type,
                    candidate_contexts, candidate_keys
                FROM edinet_cash_flow_statement
                UNION
                SELECT
                    doc_id, sec_code, submission_date, report_type,
                    candidate_contexts, candidate_keys
                FROM edinet_profit_and_loss
                UNION
                SELECT
                    doc_id, sec_code, submission_date, report_type,
                    candidate_contexts, candidate_keys
                FROM edinet_stock_dividend
            )
            """

            src_cursor = self.src_conn.cursor()
            src_cursor.execute(union_query)
            rows = src_cursor.fetchall()

            logger.info(f"ソースから {len(rows)} 件のドキュメント情報を取得")

            # 宛先DBに INSERT OR IGNORE
            insert_query = """
            INSERT OR IGNORE INTO edinet_document
            (doc_id, sec_code, submission_date, report_type, candidate_contexts, candidate_keys)
            VALUES (?, ?, ?, ?, ?, ?)
            """

            insert_count = 0
            for row in rows:
                try:
                    cursor.execute(insert_query, row)
                    insert_count += 1
                except sqlite3.Error as e:
                    logger.warning(f"INSERT失敗 (doc_id={row[0]}): {e}")

            self.dest_conn.commit()
            logger.info(f"edinet_document に {insert_count} 件を挿入")

        except sqlite3.Error as e:
            logger.error(f"edinet_document 構築中のエラー: {e}")
            self.dest_conn.rollback()
            raise

    def step3_build_mapping_dict(self) -> None:
        """
        STEP 3: 宛先の edinet_document から (doc_id → id) の辞書を構築
        """
        logger.info("=" * 60)
        logger.info("STEP 3: マッピング辞書を構築")
        logger.info("=" * 60)

        try:
            cursor = self.dest_conn.cursor()
            cursor.execute("SELECT id, doc_id FROM edinet_document")
            rows = cursor.fetchall()

            self.doc_id_mapping = {row[1]: row[0] for row in rows}
            logger.info(f"マッピング辞書に {len(self.doc_id_mapping)} 件を登録")

        except sqlite3.Error as e:
            logger.error(f"マッピング辞書構築中のエラー: {e}")
            raise

    def copy_cash_flow_statement(self) -> int:
        """
        STEP 4-1: edinet_cash_flow_statement をコピー
        """
        logger.info("-" * 60)
        logger.info("コピー中: edinet_cash_flow_statement")
        logger.info("-" * 60)

        try:
            src_cursor = self.src_conn.cursor()
            dest_cursor = self.dest_conn.cursor()

            src_cursor.execute("SELECT * FROM edinet_cash_flow_statement")
            src_rows = src_cursor.fetchall()

            insert_count = 0
            skip_count = 0

            insert_query = """
            INSERT INTO edinet_cash_flow_statement
            (period_end_date, fiscal_year, operating_cf, is_consolidated,
             id, created_at, updated_at, edinet_document_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            for row in src_rows:
                doc_id = row["doc_id"]

                # マッピング辞書から edinet_document_id を取得
                if doc_id not in self.doc_id_mapping:
                    logger.warning(f"マッピング失敗: doc_id={doc_id} (スキップ)")
                    skip_count += 1
                    continue

                edinet_document_id = self.doc_id_mapping[doc_id]

                try:
                    dest_cursor.execute(
                        insert_query,
                        (
                            row["period_end_date"],
                            row["fiscal_year"],
                            row["operating_cf"],
                            row["is_consolidated"],
                            row["id"],
                            row["created_at"],
                            row["updated_at"],
                            edinet_document_id,
                        ),
                    )
                    insert_count += 1
                except sqlite3.Error as e:
                    logger.warning(f"INSERT失敗 (id={row['id']}, doc_id={doc_id}): {e}")
                    skip_count += 1

            self.dest_conn.commit()
            logger.info(
                f"edinet_cash_flow_statement: {insert_count} 件挿入, {skip_count} 件スキップ"
            )
            return insert_count

        except sqlite3.Error as e:
            logger.error(f"edinet_cash_flow_statement コピー中のエラー: {e}")
            self.dest_conn.rollback()
            raise

    def copy_profit_and_loss(self) -> int:
        """
        STEP 4-2: edinet_profit_and_loss をコピー
        """
        logger.info("-" * 60)
        logger.info("コピー中: edinet_profit_and_loss")
        logger.info("-" * 60)

        try:
            src_cursor = self.src_conn.cursor()
            dest_cursor = self.dest_conn.cursor()

            src_cursor.execute("SELECT * FROM edinet_profit_and_loss")
            src_rows = src_cursor.fetchall()

            insert_count = 0
            skip_count = 0

            insert_query = """
            INSERT INTO edinet_profit_and_loss
            (period_end_date, fiscal_year, net_sales, operating_income, eps,
             is_consolidated, id, created_at, updated_at, edinet_document_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for row in src_rows:
                doc_id = row["doc_id"]

                # マッピング辞書から edinet_document_id を取得
                if doc_id not in self.doc_id_mapping:
                    logger.warning(f"マッピング失敗: doc_id={doc_id} (スキップ)")
                    skip_count += 1
                    continue

                edinet_document_id = self.doc_id_mapping[doc_id]

                try:
                    dest_cursor.execute(
                        insert_query,
                        (
                            row["period_end_date"],
                            row["fiscal_year"],
                            row["net_sales"],
                            row["operating_income"],
                            row["eps"],
                            row["is_consolidated"],
                            row["id"],
                            row["created_at"],
                            row["updated_at"],
                            edinet_document_id,
                        ),
                    )
                    insert_count += 1
                except sqlite3.Error as e:
                    logger.warning(f"INSERT失敗 (id={row['id']}, doc_id={doc_id}): {e}")
                    skip_count += 1

            self.dest_conn.commit()
            logger.info(f"edinet_profit_and_loss: {insert_count} 件挿入, {skip_count} 件スキップ")
            return insert_count

        except sqlite3.Error as e:
            logger.error(f"edinet_profit_and_loss コピー中のエラー: {e}")
            self.dest_conn.rollback()
            raise

    def copy_stock_dividend(self) -> int:
        """
        STEP 4-3: edinet_stock_dividend をコピー
        """
        logger.info("-" * 60)
        logger.info("コピー中: edinet_stock_dividend")
        logger.info("-" * 60)

        try:
            src_cursor = self.src_conn.cursor()
            dest_cursor = self.dest_conn.cursor()

            src_cursor.execute("SELECT * FROM edinet_stock_dividend")
            src_rows = src_cursor.fetchall()

            insert_count = 0
            skip_count = 0

            insert_query = """
            INSERT INTO edinet_stock_dividend
            (period_end_date, fiscal_year, dividend_actual, dividend_adj,
             is_consolidated, id, created_at, updated_at, edinet_document_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            for row in src_rows:
                doc_id = row["doc_id"]

                # マッピング辞書から edinet_document_id を取得
                if doc_id not in self.doc_id_mapping:
                    logger.warning(f"マッピング失敗: doc_id={doc_id} (スキップ)")
                    skip_count += 1
                    continue

                edinet_document_id = self.doc_id_mapping[doc_id]

                try:
                    dest_cursor.execute(
                        insert_query,
                        (
                            row["period_end_date"],
                            row["fiscal_year"],
                            row["dividend_actual"],
                            row["dividend_adj"],
                            row["is_consolidated"],
                            row["id"],
                            row["created_at"],
                            row["updated_at"],
                            edinet_document_id,
                        ),
                    )
                    insert_count += 1
                except sqlite3.Error as e:
                    logger.warning(f"INSERT失敗 (id={row['id']}, doc_id={doc_id}): {e}")
                    skip_count += 1

            self.dest_conn.commit()
            logger.info(f"edinet_stock_dividend: {insert_count} 件挿入, {skip_count} 件スキップ")
            return insert_count

        except sqlite3.Error as e:
            logger.error(f"edinet_stock_dividend コピー中のエラー: {e}")
            self.dest_conn.rollback()
            raise

    def step4_copy_all_tables(self) -> dict:
        """
        STEP 4: 全テーブルをコピー
        """
        logger.info("=" * 60)
        logger.info("STEP 4: EDINETテーブルをコピー")
        logger.info("=" * 60)

        try:
            # FK制約を一時的に無効化
            dest_cursor = self.dest_conn.cursor()
            dest_cursor.execute("PRAGMA foreign_keys = OFF")

            counts = {
                "edinet_cash_flow_statement": self.copy_cash_flow_statement(),
                "edinet_profit_and_loss": self.copy_profit_and_loss(),
                "edinet_stock_dividend": self.copy_stock_dividend(),
            }

            # FK制約を有効化
            dest_cursor.execute("PRAGMA foreign_keys = ON")
            self.dest_conn.commit()
            logger.info("FK制約を有効化しました")

            return counts

        except Exception as e:
            logger.error(f"テーブルコピー中のエラー: {e}")
            self.dest_conn.rollback()
            raise

    def step5_validate_and_report(self, copy_counts: dict) -> None:
        """
        STEP 5: 検証と統計出力
        """
        logger.info("=" * 60)
        logger.info("STEP 5: 検証と統計出力")
        logger.info("=" * 60)

        try:
            src_cursor = self.src_conn.cursor()
            dest_cursor = self.dest_conn.cursor()

            src_tables = [
                "edinet_cash_flow_statement",
                "edinet_profit_and_loss",
                "edinet_stock_dividend",
            ]
            dest_tables = [
                "edinet_document",
                "edinet_cash_flow_statement",
                "edinet_profit_and_loss",
                "edinet_stock_dividend",
            ]

            logger.info("-" * 60)
            logger.info("宛先DBの行数")
            logger.info("-" * 60)
            for table_name in dest_tables:
                count = self.get_table_count(self.dest_conn, table_name)
                logger.info(f"{table_name}: {count} 行")

            logger.info("-" * 60)
            logger.info("ソース vs 宛先の比較")
            logger.info("-" * 60)
            for table_name in src_tables:
                src_count = self.get_table_count(self.src_conn, table_name)
                dest_count = copy_counts.get(table_name, 0)
                logger.info(f"{table_name}: ソース {src_count} → 宛先 {dest_count}")

        except sqlite3.Error as e:
            logger.error(f"検証中のエラー: {e}")
            raise

    def run(self) -> bool:
        """
        全ステップを実行
        """
        start_time = datetime.now()
        logger.info(f"処理開始: {start_time}")

        try:
            self.connect()
            self.step1_cleanup_dest_tables()
            self.step2_build_edinet_document()
            self.step3_build_mapping_dict()
            copy_counts = self.step4_copy_all_tables()
            self.step5_validate_and_report(copy_counts)

            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            logger.info(f"処理完了: {end_time} (所要時間: {elapsed:.2f}秒)")
            return True

        except Exception as e:
            logger.error(f"処理失敗: {e}")
            return False

        finally:
            self.close()


def main():
    """メインエントリポイント"""
    parser = argparse.ArgumentParser(description="EDINETテーブルをソースDBから宛先DBへコピー")
    parser.add_argument(
        "--src",
        type=str,
        default=r"F:\TAKUMI\GitHub\STOCK-INVESTMENT-ANALYZER\work\db\stockdb.db",
        help="ソースDBのパス",
    )
    parser.add_argument(
        "--dest",
        type=str,
        default=r"F:\TAKUMI\DB\SQLite\stockdb_test.db",
        help="宛先DBのパス",
    )

    args = parser.parse_args()

    # パスの存在確認
    if not Path(args.src).exists():
        logger.error(f"ソースDBが見つかりません: {args.src}")
        return 1

    if not Path(args.dest).exists():
        logger.error(f"宛先DBが見つかりません: {args.dest}")
        return 1

    copier = EDINETTableCopier(args.src, args.dest)
    success = copier.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
