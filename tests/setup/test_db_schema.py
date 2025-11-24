import os
import re
from pathlib import Path

import psycopg
import pytest


def _parse_expected_tables(sql_text: str):
    # CREATE TABLE 文から（スキーマと）テーブル名を抽出します
    pattern = re.compile(
        r"CREATE\s+TABLE\s+"
        r"(?:IF\s+NOT\s+EXISTS\s+)?"
        r'(?:(?:"?([\w]+)"?)\.)?'
        r'"?([\w]+)"?',
        re.IGNORECASE,
    )
    results = []
    for m in pattern.finditer(sql_text):
        schema = m.group(1)
        table = m.group(2)
        results.append((schema, table))
    return results


def test_expected_tables_exist():
    # このテストファイルから見たリポジトリのルートを解決します
    repo_root = Path(__file__).resolve().parents[2]
    sql_file = (
        repo_root / "scripts" / "databaseSetup" / "sql" / "init_schema.sql"
    )

    if not sql_file.exists():
        pytest.skip(
            "init_schema.sql not found at expected location: " + str(sql_file)
        )

    sql_text = sql_file.read_text(encoding="utf-8")
    expected = _parse_expected_tables(sql_text)

    if not expected:
        pytest.skip("No CREATE TABLE statements found in init_schema.sql")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set; skipping DB schema test")

    # PostgreSQL の information_schema から既存テーブル一覧を取得します
    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_schema, table_name "
                "FROM information_schema.tables "
                "WHERE table_type='BASE TABLE' "
                "AND table_schema NOT IN ('pg_catalog', 'information_schema')"
            )
            rows = cur.fetchall()

    existing = {(row[0], row[1]) for row in rows}

    missing = []
    for schema, table in expected:
        if schema:
            if (schema, table) not in existing:
                missing.append(f"{schema}.{table}")
        else:
            # SQL にスキーマ指定がない場合、任意のユーザースキーマ内のテーブルを許容します
            found = any(t == table for (_, t) in existing)
            if not found:
                missing.append(table)

    assert not missing, f"Missing tables in database: {', '.join(missing)}"
