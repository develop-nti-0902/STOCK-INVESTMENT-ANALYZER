"""EDINET 用の一時ファイル管理ユーティリティ.

このモジュールはアーカイブの展開先から XBRL を検索したり、一時ファイルの
クリーンアップを行うためのヘルパ関数を提供します.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Literal, Optional

logger = logging.getLogger(__name__)


class EdinetFileManager:
    """共通の一時ファイル管理ユーティリティ.

    提供メソッド:
    - `create_temp_directory` : 一時作業ディレクトリを作成して Path を返す
    - `find_xbrl_file` : 抽出結果ディレクトリから優先順で XBRL ファイルを探索
    - `cleanup` : 指定パスを削除
    - `cleanup_old_files` : 指定ディレクトリ内の古いファイル/ディレクトリを削除
    - `get_file_info` : 指定ファイルのメタ情報を返す
    """

    def __init__(self, base_tmp_dir: Optional[Path] = None) -> None:
        """Initialize file manager.

        Args:
            base_tmp_dir: ベースとなる一時ディレクトリ（省略時はシステムの一時ディレクトリ）。
        """
        self.base_tmp_dir = Path(base_tmp_dir) if base_tmp_dir is not None else None

    def create_temp_directory(self, prefix: str = "edinet_") -> Path:
        """一時ディレクトリを作成して Path を返す。呼び出し側で `cleanup` を呼ぶこと."""
        dirpath = tempfile.mkdtemp(
            prefix=prefix, dir=(str(self.base_tmp_dir) if self.base_tmp_dir else None)
        )
        return Path(dirpath)

    def find_xbrl_file(self, base_path: Path) -> Optional[Path]:
        """抽出先ディレクトリから XBRL ファイルを探索する.

        優先順位:
        1. base_path / 'XBRL' / 'PublicDoc' 内の *.xbrl/*.xml
        2. base_path / 'PublicDoc' 内の *.xbrl/*.xml
        2. base_path.rglob('*.xbrl') / rglob('*.xml') の最初
        存在しない場合は None を返す。
        """
        try:
            # check XBRL/PublicDoc first (common EDINET archive layout)
            xbrl_public = base_path / "XBRL" / "PublicDoc"
            if xbrl_public.exists() and xbrl_public.is_dir():
                for ext in ("*.xbrl", "*.xml"):
                    for p in xbrl_public.glob(ext):
                        if p.is_file():
                            return p

            # then check PublicDoc at the root
            public_doc = base_path / "PublicDoc"
            if public_doc.exists() and public_doc.is_dir():
                for ext in ("*.xbrl", "*.xml"):
                    for p in public_doc.glob(ext):
                        if p.is_file():
                            return p

            # fallback: search recursively
            for ext in ("*.xbrl", "*.xml"):
                it = base_path.rglob(ext)
                for p in it:
                    if p.is_file():
                        return p
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("find_xbrl_file error for %s: %s", base_path, exc)
        return None

    def cleanup(self, path: Path) -> None:
        """ファイルまたはディレクトリを削除する。失敗しても例外は上げずログのみ出す."""
        try:
            if not path.exists():
                return
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("cleanup failed for %s: %s", path, exc)

    def cleanup_old_files(
        self,
        directory: Path,
        max_age: int = 24,
        unit: Literal["hours", "days"] = "hours",
        max_age_hours: Optional[int] = None,
    ) -> int:
        """指定ディレクトリ配下で古いファイル/ディレクトリを削除する.

        - `max_age`: 閾値（単位は `unit`）。
        - `unit`: `hours` or `days`。

        戻り値は削除したエントリ数。
        """
        if not directory.exists() or not directory.is_dir():
            return 0

        # Backwards-compatible: if caller passed `max_age_hours`, use it as hours
        if max_age_hours is not None:
            max_age = int(max_age_hours)
            unit = "hours"

        now = datetime.utcnow()
        delta = timedelta(hours=max_age) if unit == "hours" else timedelta(days=max_age)
        cutoff = now - delta
        removed = 0

        try:
            for child in directory.iterdir():
                try:
                    mtime = datetime.utcfromtimestamp(child.stat().st_mtime)
                    if mtime < cutoff:
                        if child.is_file():
                            child.unlink()
                        else:
                            shutil.rmtree(child)
                        removed += 1
                except Exception:
                    logger.exception("failed to evaluate/remove %s", child)
        except Exception:
            logger.exception("cleanup_old_files failed for %s", directory)

        return removed

    def get_file_info(self, file_path: Path) -> Optional[Dict[str, object]]:
        """ファイルの基本情報を返す（存在しない場合は None）."""
        try:
            if not file_path.exists() or not file_path.is_file():
                return None
            st = file_path.stat()
            return {
                "path": str(file_path),
                "size": st.st_size,
                "mtime": st.st_mtime,
            }
        except Exception:
            logger.exception("get_file_info failed for %s", file_path)
            return None
