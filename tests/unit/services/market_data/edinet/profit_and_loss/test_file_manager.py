"""Unit tests for EdinetProfitAndLossFileManager behaviors."""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.services.market_data.edinet.file_manager import (
    EdinetFileManager as EdinetProfitAndLossFileManager,
)


def test_find_xbrl_file_priority(tmp_path: Path):
    """Prefer standard XBRL PublicDoc path when locating XBRL files."""
    fm = EdinetProfitAndLossFileManager()
    base = tmp_path / "base"
    std_dir = base / "XBRL" / "PublicDoc"
    std_dir.mkdir(parents=True)
    std_file = std_dir / "doc_std.xbrl"
    std_file.write_text("dummy")

    other = base / "other_dir"
    other.mkdir()
    other_file = other / "doc_other.xbrl"
    other_file.write_text("dummy2")

    found = fm.find_xbrl_file(base)
    assert found is not None
    assert found.name == "doc_std.xbrl"


def test_cleanup_old_files_removes_old(tmp_path: Path):
    """Remove files older than configured max age and return delete count."""
    fm = EdinetProfitAndLossFileManager()
    d = tmp_path / "cleanup"
    d.mkdir()

    recent = d / "recent.txt"
    old = d / "old.txt"
    recent.write_text("r")
    old.write_text("o")

    old_time = time.time() - 3600 * 26
    os.utime(old, (old_time, old_time))

    deleted = fm.cleanup_old_files(d, max_age_hours=24)
    assert deleted == 1
    assert not old.exists()
    assert recent.exists()
