#!/usr/bin/env python3
"""Cross-platform SQLite setup and Alembic migration helper.

This consolidates the logic previously in setup_sqlite.bat and setup_sqlite.sh
into a single Python script. It prefers the behavior of the Windows batch script
when differences exist (per project request).

Usage:
  python scripts/databaseSetup/setup_sqlite.py [DB_FILE]

Defaults and priority: CLI arg > SQLITE_DB_FILE (.env) > DATABASE_URL (.env) > repo/data/sqlite.db
On Windows this script will persist `DATABASE_URL` using `setx` to match the
original batch behavior. On non-Windows it will export for the process only.
"""
from __future__ import annotations

import argparse
import os
import shlex
import sqlite3
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
                # only set if not already in environment
                if k in (
                    "SQLITE_DB_FILE",
                    "DATABASE_URL",
                    "SQLITE_JOURNAL_MODE",
                    "SQLITE_SYNCHRONOUS",
                    "SQLITE_TIMEOUT",
                    "SQLITE_FOREIGN_KEYS",
                ):
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


def ensure_dir_for(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def create_db_file_if_missing(db_path: Path) -> None:
    if db_path.exists():
        return
    # Prefer system sqlite3 binary if available
    from shutil import which

    if which("sqlite3"):
        try:
            subprocess.run(
                ["sqlite3", str(db_path), "VACUUM;"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if db_path.exists():
                return
        except Exception:
            pass

    # Fallback to Python sqlite3
    ensure_dir_for(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.close()


def normalize_to_sqlalchemy_url(db: str) -> str:
    # If already a sqlite URL, leave as-is (but normalize path form)
    if db.startswith("sqlite://"):
        # If sqlite:///path form, keep it
        return db
    # treat as file path
    p = Path(db).expanduser().resolve()
    return "sqlite:///" + str(p).replace("\\", "/")


def detect_python_cmd() -> str:
    # Prefer venvs like .venv or venv, otherwise use current interpreter
    candidates = [
        (
            REPO_ROOT / ".venv" / "Scripts" / "python.exe"
            if os.name == "nt"
            else REPO_ROOT / ".venv" / "bin" / "python"
        ),
        (
            REPO_ROOT / "venv" / "Scripts" / "python.exe"
            if os.name == "nt"
            else REPO_ROOT / "venv" / "bin" / "python"
        ),
    ]
    for c in candidates:
        try:
            if Path(c).exists():
                return str(c)
        except Exception:
            continue
    return sys.executable or "python"


def persist_database_url_windows(url: str) -> None:
    # Use setx to persist to user environment (mirror original .bat behaviour)
    try:
        subprocess.run(
            ["setx", "DATABASE_URL", url],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def run_alembic(python_cmd: str) -> int:
    # Check alembic is available
    try:
        res = subprocess.run(
            [python_cmd, "-m", "alembic", "--version"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode != 0:
            print(f"[ERROR] Alembic not found. Install: {python_cmd} -m pip install alembic")
            return 2
    except FileNotFoundError:
        print(f"[ERROR] Python executable not found: {python_cmd}")
        return 2

    try:
        subprocess.run(
            [python_cmd, "-m", "alembic", "-c", str(REPO_ROOT / "alembic.ini"), "upgrade", "heads"],
            check=True,
        )
    except subprocess.CalledProcessError:
        print("[ERROR] Alembic migration failed")
        return 3
    return 0


def call_ensure_tables(python_cmd: str) -> int:
    script = REPO_ROOT / "scripts" / "databaseSetup" / "ensure_sqlite_tables.py"
    if not script.exists():
        print("[WARN] ensure_sqlite_tables.py not found; skipping")
        return 0
    try:
        subprocess.run([python_cmd, str(script)], check=True)
    except subprocess.CalledProcessError:
        print("[ERROR] ensure_sqlite_tables.py failed")
        return 4
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup SQLite DB and run Alembic migrations")
    parser.add_argument("db_file", nargs="?", help="DB file path or sqlite URL")
    parser.add_argument(
        "--no-persist",
        dest="persist",
        action="store_false",
        help="Do not persist DATABASE_URL to user env (Windows)",
    )
    parser.set_defaults(persist=(os.name == "nt"))
    args = parser.parse_args()

    load_env_file(REPO_ROOT / ".env")

    db_choice = choose_db_file(args.db_file)

    # If it's a sqlite URL like sqlite:///..., we'll strip for file operations
    db_path = strip_sqlite_url(db_choice)
    db_path_obj = Path(db_path).expanduser()

    # If the value was a DATABASE_URL like 'sqlite:///...', the db_path may be absolute already
    ensure_dir_for(db_path_obj)
    create_db_file_if_missing(db_path_obj)

    abs_path = str(db_path_obj.resolve())
    sqlalchemy_url = normalize_to_sqlalchemy_url(
        db_choice if db_choice.startswith("sqlite://") else abs_path
    )

    python_cmd = detect_python_cmd()

    print(f"Using SQLite DB file: {abs_path}")

    # Persist DATABASE_URL on Windows by default (match batch behavior)
    if args.persist and os.name == "nt":
        persist_database_url_windows(sqlalchemy_url)
        print(f"Persisted DATABASE_URL via setx (user): {sqlalchemy_url}")
    else:
        # Export for subprocesses in this run
        os.environ.setdefault("DATABASE_URL", sqlalchemy_url)
        print(f"Exported DATABASE_URL={sqlalchemy_url}")

    # Run alembic
    rc = run_alembic(python_cmd)
    if rc != 0:
        return rc

    # Call ensure_sqlite_tables.py (will create tables if missing)
    rc = call_ensure_tables(python_cmd)
    if rc != 0:
        return rc

    print(f"[SUCCESS] SQLite DB ready: {abs_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
