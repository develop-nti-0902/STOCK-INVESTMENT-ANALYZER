"""SQLiteデータベースのテーブル存在確認ユーティリティ."""

import os
import sqlite3
import sys

# Ensure repo root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from app.models import Base  # noqa: E402


def get_expected_tables():
    """モデルメタデータから期待されるテーブル名のセットを取得."""
    return set(Base.metadata.tables.keys())


def get_actual_tables(db_path):
    """指定されたSQLiteデータベースから実際のテーブル名のセットを取得."""
    if not os.path.exists(db_path):
        print(f"DB_MISSING:{db_path}")
        return set()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    rows = cur.fetchall()
    conn.close()
    return set(r[0] for r in rows)


def main():
    """メイン実行関数: 期待するテーブルと実際のテーブルを比較."""
    db_path = (
        os.environ.get("SQLITE_DB_FILE")
        or os.environ.get("DATABASE_URL")
        or os.path.join(REPO_ROOT, "data", "sqlite.db")
    )
    # If DATABASE_URL is a sqlite URL, strip prefix
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")

    expected = get_expected_tables()
    actual = get_actual_tables(db_path)

    print("DB_PATH:" + db_path)
    print("EXPECTED_COUNT:" + str(len(expected)))
    print("ACTUAL_COUNT:" + str(len(actual)))
    missing = expected - actual
    extra = actual - expected
    print("\nMISSING_TABLES:")
    for t in sorted(missing):
        print(t)
    print("\nEXTRA_TABLES:")
    for t in sorted(extra):
        print(t)


if __name__ == "__main__":
    main()
