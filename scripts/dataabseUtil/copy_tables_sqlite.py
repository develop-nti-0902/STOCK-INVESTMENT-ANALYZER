"""SQLiteテーブルコピー用スクリプト

ソース: 任意のSQLiteファイル
宛先: 任意のSQLiteファイル
指定テーブルをコピーし、宛先に既存データがあれば削除して上書きします。

Usage (既定のパスを使う例):
    poetry run python scripts/dataabseUtil/copy_tables_sqlite.py

もしくはパスを指定:
    poetry run python scripts/dataabseUtil/copy_tables_sqlite.py \
        --source "F:/TAKUMI/GitHub/STOCK-INVESTMENT-ANALYZER/work/db/stockdb.db" \
        --dest "F:/TAKUMI/DB/SQLite/stockdb_test.db" \
        --tables stocks_1d stocks_1m
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from typing import Iterable, List


def ensure_table_exists_in_dest(
    src_conn: sqlite3.Connection, dest_conn: sqlite3.Connection, table: str
) -> None:
    cur = dest_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    if cur.fetchone():
        return
    # get create sql from source
    cur = src_conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
    row = cur.fetchone()
    if not row or not row[0]:
        raise RuntimeError(f"ソースにテーブルが存在しません: {table}")
    create_sql = row[0]
    dest_conn.execute(create_sql)
    dest_conn.commit()


def copy_table_with_progress(
    src_conn: sqlite3.Connection,
    dest_conn: sqlite3.Connection,
    table: str,
    batch_size: int = 10000,
    commit_every: int = 100000,
) -> None:
    print(f"[{datetime.now().isoformat()}] [{table}] 宛先テーブル存在確認/作成を開始します...")
    sys.stdout.flush()
    ensure_table_exists_in_dest(src_conn, dest_conn, table)
    print(f"[{datetime.now().isoformat()}] [{table}] 宛先テーブル準備完了")
    sys.stdout.flush()

    print(f"[{datetime.now().isoformat()}] [{table}] 宛先テーブルの既存データを削除します...")
    dest_conn.execute(f"DELETE FROM {table}")
    dest_conn.commit()
    print(f"[{datetime.now().isoformat()}] [{table}] 削除完了")
    sys.stdout.flush()

    print(f"[{datetime.now().isoformat()}] [{table}] ソースからレコード読み取り開始...")
    src_cur = src_conn.execute(f"SELECT * FROM {table}")
    col_count = len(src_cur.description)
    placeholders = ",".join(["?"] * col_count)
    insert_sql = f"INSERT INTO {table} VALUES ({placeholders})"

    copied = 0
    rows_since_commit = 0

    # Begin a transaction to allow grouped commits for better throughput
    try:
        dest_conn.execute("BEGIN")
    except Exception:
        # Some SQLite wrappers/versions may not allow explicit BEGIN; proceed anyway
        pass

    try:
        while True:
            rows = src_cur.fetchmany(batch_size)
            if not rows:
                break
            dest_conn.executemany(insert_sql, rows)
            copied += len(rows)
            rows_since_commit += len(rows)

            # Commit when accumulated rows reach threshold
            if commit_every > 0 and rows_since_commit >= commit_every:
                dest_conn.commit()
                try:
                    dest_conn.execute("BEGIN")
                except Exception:
                    pass
                rows_since_commit = 0

            sys.stdout.write(f"\r[{datetime.now().isoformat()}] {table}: {copied} 行コピー中...")
            sys.stdout.flush()

        # Final commit for remaining rows
        if rows_since_commit > 0:
            dest_conn.commit()

    except Exception:
        # On error, ensure we attempt to commit whatever is pending to avoid losing progress
        try:
            dest_conn.commit()
        except Exception:
            pass
        raise

    finally:
        sys.stdout.write("\n")
        print(
            f"[{datetime.now().isoformat()}] [{table}] コピー完了。合計 {copied} 行をコピーしました。"
        )
    sys.stdout.flush()


def copy_tables(
    source: str,
    dest: str,
    tables: Iterable[str],
    batch_size: int = 1000,
    commit_every: int = 100000,
) -> None:
    if not os.path.exists(source):
        raise FileNotFoundError(f"Source DB not found: {source}")
    # 宛先DBのディレクトリがなければ作る
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    src_conn = sqlite3.connect(source)
    dest_conn = sqlite3.connect(dest)

    # Apply pragmas to speed up large imports on destination
    try:
        dest_conn.execute("PRAGMA synchronous = OFF")
        dest_conn.execute("PRAGMA journal_mode = WAL")
        dest_conn.execute("PRAGMA temp_store = MEMORY")
        dest_conn.execute("PRAGMA mmap_size = 30000000000")
        print(f"[{datetime.now().isoformat()}] 宛先DBのPRAGMAを設定しました")
    except Exception:
        # PRAGMA が利用できない環境でも継続
        print(f"[{datetime.now().isoformat()}] PRAGMA 設定に失敗しましたが処理を継続します")
    sys.stdout.flush()

    try:
        for table in tables:
            # テーブルがソースにあるか確認
            cur = src_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
            )
            if not cur.fetchone():
                print(f"警告: ソースにテーブルが見つかりません: {table} — スキップします。")
                continue
            copy_table_with_progress(
                src_conn, dest_conn, table, batch_size=batch_size, commit_every=commit_every
            )
    finally:
        src_conn.close()
        dest_conn.close()


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Copy specific tables from one SQLite DB to another with progress output."
    )
    p.add_argument(
        "--source",
        default=r"F:/TAKUMI/GitHub/STOCK-INVESTMENT-ANALYZER/work/db/stockdb.db",
        help="Source SQLite DB path",
    )
    p.add_argument(
        "--dest", default=r"F:/TAKUMI/DB/SQLite/stockdb_test.db", help="Destination SQLite DB path"
    )
    p.add_argument(
        "--tables",
        nargs="+",
        default=["stocks_1d", "stocks_1m"],
        help="Tables to copy (space separated)",
    )
    p.add_argument("--batch", type=int, default=10000, help="Batch size for inserting rows")
    p.add_argument(
        "--commit-every",
        type=int,
        default=100000,
        help="Number of rows to accumulate before issuing a commit (0 = commit every batch)",
    )
    args = p.parse_args(argv)

    print("Source:", args.source)
    print("Destination:", args.dest)
    print("Tables:", ", ".join(args.tables))

    try:
        copy_tables(
            args.source,
            args.dest,
            args.tables,
            batch_size=args.batch,
            commit_every=args.commit_every,
        )
    except Exception as e:
        print("エラーが発生しました:", e)
        return 1
    print("すべてのテーブルコピーが完了しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
