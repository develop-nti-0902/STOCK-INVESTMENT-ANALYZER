"""Unit tests for TempFileManagerMixin."""

from app.services.core.file_managers.temp_file_manager_mixin import TempFileManagerMixin


class C(TempFileManagerMixin):
    """テスト用のクラス（TempFileManagerMixin を注入)."""

    pass


def test_tempdir_context_manager(tmp_path):
    """create_temp_directory と cleanup の基本動作を確認する."""
    c = C()
    # ensure create_temp_directory returns a Path
    d = c.create_temp_directory()
    assert d.exists() or d
    # cleanup should not raise
    c.cleanup(d)
