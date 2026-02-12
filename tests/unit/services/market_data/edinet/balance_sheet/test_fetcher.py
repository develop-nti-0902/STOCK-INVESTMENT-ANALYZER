"""EDINET ドキュメントフェッチャの単体テスト."""

import shutil
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from app.services.market_data.edinet.download_service import EdinetDownloadService


class _MockClient:
    """zip バイト列を返すダミー API クライアント."""

    def __init__(self, zip_bytes: bytes):
        self._zip = zip_bytes

    async def download_document(self, doc_id: str) -> bytes:
        return self._zip


def _make_sample_zip() -> bytes:
    """サンプルの ZIP バイト列を作成します (XBRL を含む構造)."""
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        # create nested path similar to EDINET layout
        z.writestr("SAMPLE/XBRL/PublicDoc/sample.xbrl", "<xbrl>TEST</xbrl>")
    return bio.getvalue()


@pytest.mark.asyncio
async def test_fetch_writes_and_returns_xbrl(tmp_path):
    """fetch が XBRL ファイルを書き出し、パスを返すことを検証します."""
    zip_bytes = _make_sample_zip()
    client = _MockClient(zip_bytes)
    work_dir = tmp_path / "edinet_work"
    svc = EdinetDownloadService(api_client=client, work_dir=work_dir)

    xbrl_path = await svc.download_and_extract("SAMPLE")
    assert xbrl_path.exists()
    assert xbrl_path.suffix == ".xbrl"
    content = xbrl_path.read_text()
    assert "TEST" in content

    # cleanup
    shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_fetch_batch_returns_list(tmp_path):
    """複数 ID を fetch_batch で処理できることを検証します."""
    zip_bytes = _make_sample_zip()
    client = _MockClient(zip_bytes)
    work_dir = tmp_path / "edinet_work"
    svc = EdinetDownloadService(api_client=client, work_dir=work_dir)

    # emulate batch by concurrently calling download_and_extract
    import asyncio

    tasks = [asyncio.create_task(svc.download_and_extract(i)) for i in ("A", "B", "C")]
    results = await asyncio.gather(*tasks)
    assert isinstance(results, list)
    assert len(results) == 3
    for p in results:
        assert Path(p).exists()

    shutil.rmtree(work_dir)
