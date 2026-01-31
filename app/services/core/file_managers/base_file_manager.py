from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class BaseFileManager(ABC):
    """ファイル管理の抽象基底クラス。

    一時ディレクトリ作成やクリーンアップなどを定義します。
    """

    @abstractmethod
    def create_temp_directory(self, *args: Any, **kwargs: Any) -> Path:
        """一時ディレクトリを作成して `Path` を返す。"""

    @abstractmethod
    def cleanup(self, path: Path) -> None:
        """指定したパスを削除する（安全に）。"""
