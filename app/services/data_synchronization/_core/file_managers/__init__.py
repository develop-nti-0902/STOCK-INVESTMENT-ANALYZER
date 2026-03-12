"""
ファイル管理抽象化モジュール.

サービス層における共通ファイル管理の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.data_synchronization._core.file_managers.base_file_manager import BaseFileManager
from app.services.data_synchronization._core.file_managers.temp_file_manager_mixin import (
    TempFileManagerMixin,
)

__all__ = ["BaseFileManager", "TempFileManagerMixin"]
