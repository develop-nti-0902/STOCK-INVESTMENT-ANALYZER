#!/usr/bin/env python3
"""Cross-platform teardown for SQLite DB file.

Usage:
  python scripts/databaseSetup/teardown_sqlite.py [DB_FILE]

Priority: CLI arg > SQLITE_DB_FILE (.env) > DATABASE_URL (.env) > repo/data/sqlite.db
This mirrors the previous teardown_sqlite.bat behavior.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"')
                if k in ("SQLITE_DB_FILE", "DATABASE_URL"):
                    os.environ.setdefault(k, v)
    except Exception:
        pass


def choose_db_file(cli_arg: Optional[str]) -> str:
    if cli_arg:
        return cli_arg
    if os.environ.get("SQLITE_DB_FILE"):
        return os.environ["SQLITE_DB_FILE"]
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    return str(REPO_ROOT / "data" / "sqlite.db")


def strip_sqlite_url(db: str) -> str:
    if db.startswith("sqlite:///"):
        return db.replace("sqlite:///", "")
    return db


def check_alembic_available(python_cmd: str) -> bool:
    try:
        res = subprocess.run(
            [python_cmd, "-m", "alembic", "--version"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return res.returncode == 0
    except Exception:
        return False


def make_writable_and_delete(path: Path) -> None:
    try:
        if path.exists():
            # attempt to make writable (handles read-only flags on Windows)
            try:
                path.chmod(0o666)
            except Exception:
                pass
            path.unlink()
    except Exception as e:
        raise


def main() -> int:
    db_arg = None
    if len(sys.argv) > 1:
        db_arg = sys.argv[1]

    load_env_file(REPO_ROOT / ".env")
    db_value = choose_db_file(db_arg)
    db_path_str = strip_sqlite_url(db_value)
    db_path = Path(db_path_str).expanduser()

    # Normalize path on Windows-style inputs
    try:
        db_path = db_path.resolve()
    except Exception:
        db_path = db_path

    print(f"Using SQLite DB file: {db_path}")

    python_cmd = sys.executable or "python"

    if not db_path.exists():
        print(f"[INFO] DB file does not exist: {db_path} — nothing to teardown")
        return 0

    if not check_alembic_available(python_cmd):
        print(f"[ERROR] Alembic not found. Install: {python_cmd} -m pip install alembic")
        return 1

    # Delete DB file (we skip alembic downgrade and directly remove the file)
    try:
        print(f"Deleting DB file: {db_path}")
        make_writable_and_delete(db_path)
    except Exception as e:
        print(f"[ERROR] Failed to delete DB file: {db_path} — {e}")
        return 1

    print(f"[SUCCESS] SQLite DB file removed: {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
