"""Ensure SQLite has expected tables; if missing, create them from model metadata."""

import os
import sys
from typing import Set

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, REPO_ROOT)

from sqlalchemy import create_engine

from app.models import Base  # noqa: E402


def _get_db_path_or_url() -> str:
    """Return a DB URL or sqlite path from env vars or defaults."""
    db = os.environ.get("DATABASE_URL") or os.environ.get("SQLITE_DB_FILE")
    if not db:
        db = os.path.join(REPO_ROOT, "data", "sqlite.db")
    return db


def _normalize_sqlite_path(db: str) -> str:
    if db.startswith("sqlite:///"):
        return db.replace("sqlite:///", "")
    return db


def get_expected_tables() -> Set[str]:
    return set(Base.metadata.tables.keys())


def get_actual_tables(db_path: str) -> Set[str]:
    import sqlite3

    if not os.path.exists(db_path):
        return set()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    rows = cur.fetchall()
    conn.close()
    return set(r[0] for r in rows)


def create_tables(db_url: str) -> None:
    is_sqlite = db_url.startswith("sqlite:") or os.path.exists(db_url)
    if db_url.startswith("sqlite:///"):
        engine = create_engine(db_url, connect_args={"check_same_thread": False})
    elif is_sqlite and not db_url.startswith("sqlite://"):
        # treat as file path
        path = db_url
        url = "sqlite:///" + path.replace("\\", "/")
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(db_url)

    Base.metadata.create_all(bind=engine)
    engine.dispose()


def main() -> int:
    db = _get_db_path_or_url()
    db_path = _normalize_sqlite_path(db)

    expected = get_expected_tables()
    actual = get_actual_tables(db_path)

    missing = expected - actual
    print(f"DB_PATH:{db_path}")
    print(f"EXPECTED_COUNT:{len(expected)}")
    print(f"ACTUAL_COUNT:{len(actual)}")
    if not expected:
        print("[WARN] No tables defined in metadata (expected=0)")
        return 0

    if missing:
        print(
            f"[INFO] Missing {len(missing)} tables, creating from metadata: {sorted(missing)[:10]}"
        )
        try:
            create_tables(db)
        except Exception as e:
            print(f"[ERROR] Failed to create tables: {e}")
            return 2

        # re-check
        actual2 = get_actual_tables(db_path)
        missing2 = expected - actual2
        if missing2:
            print(f"[ERROR] Still missing tables after create_all: {sorted(missing2)}")
            return 3
        print("[SUCCESS] Created missing tables")
        return 0

    print("[OK] All expected tables present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
