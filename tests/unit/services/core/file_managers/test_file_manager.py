from __future__ import annotations

from pathlib import Path

from app.services.core.file_managers.temp_file_manager_mixin import (
    TempFileManagerMixin,
)


class _Dummy(TempFileManagerMixin):
    pass


def test_tempdir_create_and_cleanup():
    d = _Dummy()
    path = d.create_temp_directory(prefix="test_edinet_")
    assert isinstance(path, Path)
    assert path.exists()

    # cleanup should remove the directory
    d.cleanup(path)
    assert not path.exists()
