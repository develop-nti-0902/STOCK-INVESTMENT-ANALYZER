from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.services.core.file_managers.base_file_manager import BaseFileManager
from app.services.core.file_managers.temp_file_manager_mixin import (
    TempFileManagerMixin,
)


class EdinetFileManager(BaseFileManager, TempFileManagerMixin):
    """EDINET向けの一時ファイル管理ユーティリティ。

    - 一時ディレクトリの作成・クリーンアップ
    - XBRLファイルの探索
    - 古い一時ファイルの定期削除（ローテーション）
    """

    def create_temp_directory(self, prefix: str = "edinet_") -> Path:
        # 明示的に TempFileManagerMixin の実装を呼ぶ
        return TempFileManagerMixin.create_temp_directory(self, prefix=prefix)

    def cleanup(self, path: Path) -> None:
        # 明示的に TempFileManagerMixin の実装を呼ぶ
        return TempFileManagerMixin.cleanup(self, path)

    def find_xbrl_file(self, base_path: Path) -> Optional[Path]:
        """base_path の下から XBRL ファイル（拡張子 .xbrl）を探索して最初のパスを返す。

        探索順序:
        1. base_path / "XBRL" / "PublicDoc" 以下
        2. base_path 以下を再帰探索

        見つからなければ None を返す。
        """
        candidates = []

        # まず標準的な場所を優先
        xbrl_public = base_path / "XBRL" / "PublicDoc"
        if xbrl_public.exists():
            for p in xbrl_public.rglob("*.xbrl"):
                candidates.append(p)
            if candidates:
                return candidates[0]

        # 次に base_path 以下を幅優先で検索して最初の .xbrl を返す
        for p in base_path.rglob("*.xbrl"):
            return p

        return None

    def cleanup_old_files(self, base_dir: Path, max_age_days: int = 7) -> int:
        """base_dir の下にある一時ディレクトリを走査し、最終更新日時が
        `max_age_days` より古いものを削除する。削除したエントリ数を返す。
        """
        if not base_dir.exists():
            return 0

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max_age_days)
        removed = 0

        for child in base_dir.iterdir():
            try:
                mtime = datetime.fromtimestamp(
                    child.stat().st_mtime, timezone.utc
                )
                if mtime < cutoff:
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                    removed += 1
            except FileNotFoundError:
                # 既に消えている可能性があるので無視
                continue
            except Exception:
                # ログ依存を避けるためここでは無視する
                continue

        return removed
