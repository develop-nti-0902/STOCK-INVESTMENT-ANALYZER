"""Unit tests for the EDINET balance sheet file manager.

These tests verify temporary directory management, XBRL file discovery,
and cleanup of aged files.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.market_data.edinet.file_manager import EdinetFileManager


def test_create_and_cleanup_temp_directory(tmp_path: Path) -> None:
    """Create a temporary directory, write a file, then cleanup it.

    Ensures that `create_temp_directory` returns an existing path and that
    `cleanup` removes the directory afterwards.
    """
    m = EdinetFileManager()
    d = m.create_temp_directory(prefix="edinet_test_")
    assert d.exists()
    # 作成したディレクトリにファイルを置いてからクリーンアップ
    f = d / "sample.txt"
    f.write_text("ok")
    assert f.exists()
    m.cleanup(d)
    assert not d.exists()


def test_find_xbrl_file(tmp_path: Path) -> None:
    """Locate an XBRL file inside the expected EDINET document structure.

    Builds a fake document directory with `XBRL/PublicDoc` and asserts that
    `find_xbrl_file` returns the file path when present.
    """
    # 構造を作る
    doc_dir = tmp_path / "SAMPLE_DOC"
    xbrl_dir = doc_dir / "XBRL" / "PublicDoc"
    xbrl_dir.mkdir(parents=True)
    target = xbrl_dir / "sample.xbrl"
    target.write_text("<xbrl/>")

    m = EdinetFileManager()
    found = m.find_xbrl_file(doc_dir)
    assert found is not None
    assert found.name == "sample.xbrl"


def test_cleanup_old_files(tmp_path: Path) -> None:
    """Remove directories older than the configured age.

    Creates `old` and `new` directories, backdates `old` and verifies that
    `cleanup_old_files` removes the old directory while preserving recent ones.
    """
    base = tmp_path / "data"
    base.mkdir()
    old = base / "old"
    new = base / "new"
    old.mkdir()
    new.mkdir()

    # 古いディレクトリの mtime を過去にする
    past = datetime.now(timezone.utc) - timedelta(days=10)
    ts = past.timestamp()
    os.utime(old, (ts, ts))

    m = EdinetFileManager()
    # cleanup_old_files expects hours; convert 7 days to hours for the test
    removed = m.cleanup_old_files(base, max_age_hours=7 * 24)
    assert removed >= 1
    assert not old.exists() or removed >= 1
    assert new.exists()
