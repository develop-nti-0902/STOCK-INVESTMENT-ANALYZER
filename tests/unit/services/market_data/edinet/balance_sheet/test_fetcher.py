import shutil
import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from app.services.market_data.edinet.balance_sheet.fetcher import (
    EdinetDocumentFetcher,
)


class _MockClient:
    def __init__(self, zip_bytes: bytes):
        self._zip = zip_bytes

    async def download_document(self, doc_id: str) -> bytes:
        return self._zip


def _make_sample_zip() -> bytes:
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        # create nested path similar to EDINET layout
        z.writestr("SAMPLE/XBRL/PublicDoc/sample.xbrl", "<xbrl>TEST</xbrl>")
    return bio.getvalue()


@pytest.mark.asyncio
async def test_fetch_writes_and_returns_xbrl(tmp_path):
    zip_bytes = _make_sample_zip()
    client = _MockClient(zip_bytes)
    work_dir = tmp_path / "edinet_work"
    fetcher = EdinetDocumentFetcher(api_client=client, work_dir=work_dir)

    xbrl_path = await fetcher.fetch("SAMPLE")
    assert xbrl_path.exists()
    assert xbrl_path.suffix == ".xbrl"
    content = xbrl_path.read_text()
    assert "TEST" in content

    # cleanup
    shutil.rmtree(work_dir)


@pytest.mark.asyncio
async def test_fetch_batch_returns_list(tmp_path):
    zip_bytes = _make_sample_zip()
    client = _MockClient(zip_bytes)
    work_dir = tmp_path / "edinet_work"
    fetcher = EdinetDocumentFetcher(api_client=client, work_dir=work_dir)

    results = await fetcher.fetch_batch(["A", "B", "C"], concurrency=2)
    assert isinstance(results, list)
    assert len(results) == 3
    for p in results:
        assert Path(p).exists()

    shutil.rmtree(work_dir)
