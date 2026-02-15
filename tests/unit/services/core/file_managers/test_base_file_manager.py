"""Unit tests for BaseFileManager implementations."""

from pathlib import Path

from app.services.core.file_managers.base_file_manager import BaseFileManager


class DummyManager(BaseFileManager):
    """テスト用の最小実装マネージャー（BaseFileManager 継承)."""

    def create_temp_directory(self, *args, **kwargs) -> Path:
        """一時ディレクトリを作成して Path を返す（テスト用の簡易実装)."""
        return Path.cwd()

    def cleanup(self, path: Path) -> None:
        """指定パスのクリーンアップを行う（テスト用ダミー)."""
        return None


def test_base_file_manager_subclass_instantiation():
    """DummyManager のインスタンス化と create_temp_directory の動作確認."""
    m = DummyManager()
    assert m.create_temp_directory() is not None
