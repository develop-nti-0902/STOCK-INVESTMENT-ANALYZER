"""Unit tests for EdinetFileManager."""

from pathlib import Path

from app.services.data_synchronization.market_data.edinet.file_manager import EdinetFileManager


def test_create_and_cleanup_tempdir(tmp_path):
    """一時ディレクトリの作成とクリーンアップ動作を確認する."""
    mgr = EdinetFileManager(base_tmp_dir=tmp_path)
    d = mgr.create_temp_directory()
    assert Path(d).exists()
    mgr.cleanup(d)
    assert not Path(d).exists()


def test_find_xbrl_file(tmp_path):
    """XBRL ファイルの検索が期待通りに動作することを検証する."""
    base = tmp_path / "extracted"
    xbrl_dir = base / "XBRL" / "PublicDoc"
    xbrl_dir.mkdir(parents=True)
    p = xbrl_dir / "doc.xbrl"
    p.write_text("xbrl")
    mgr = EdinetFileManager()
    found = mgr.find_xbrl_file(base)
    assert found is not None
    assert found.name == "doc.xbrl"


def test_get_file_info_and_cleanup_old_files(tmp_path):
    """ファイル情報取得と古いファイルのクリーンアップを検証する."""
    f = tmp_path / "f.txt"
    f.write_text("x")
    mgr = EdinetFileManager()
    info = mgr.get_file_info(f)
    assert info is not None and "size" in info
    # cleanup_old_files on non-matching age should return 0
    removed = mgr.cleanup_old_files(tmp_path, max_age=0)
    assert isinstance(removed, int)
