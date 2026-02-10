"""テンポラリファイル管理のユーティリティMixin.

一時ディレクトリの作成や安全な削除、コンテキストジェネレータを提供します.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Iterator


class TempFileManagerMixin:
    """テンポラリディレクトリ作成・削除の共通Mixin.

    `create_temp_directory` はコンテキストマネージャーとしても使える。
    """

    def create_temp_directory(self, prefix: str = "edinet_") -> Path:
        """一時ディレクトリを作成して Path を返す."""
        dirpath = Path(tempfile.mkdtemp(prefix=prefix))
        return dirpath

    def cleanup(self, path: Path) -> None:
        """ディレクトリまたはファイルを安全に削除する。存在しなければ何もしない."""
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except Exception:
            # ここではログを出す想定だが、依存を増やさないため無視する
            pass

    def tempdir_context(self, prefix: str = "edinet_") -> Iterator[Path]:
        """コンテキストマネージャとして一時ディレクトリを提供するジェネレータ.

        Usage:
            with obj.tempdir_context() as d:
                ...
        """
        dirpath = self.create_temp_directory(prefix=prefix)
        try:
            yield dirpath
        finally:
            self.cleanup(dirpath)
