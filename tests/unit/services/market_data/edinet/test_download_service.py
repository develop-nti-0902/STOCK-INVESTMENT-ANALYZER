import asyncio
import tempfile
from pathlib import Path

import pytest

from app.services.market_data.edinet.download_service import EdinetDownloadService


class DummyAPIClient:
    def __init__(self, zip_bytes: bytes):
        self._zip = zip_bytes

    async def download_document(self, doc_id: str) -> bytes:
        await asyncio.sleep(0)
        return self._zip


@pytest.mark.asyncio
async def test_download_and_extract_and_root(tmp_path):
    # create a simple xml/xbrl file
    xml_content = b"<root><child>value</child></root>"
    file_path = tmp_path / "sample.xbrl"
    file_path.write_bytes(xml_content)

    # build a zip containing the sample xbrl
    import zipfile
    from io import BytesIO

    bio = BytesIO()
    with zipfile.ZipFile(bio, "w") as z:
        z.writestr("SAMPLE/XBRL/PublicDoc/sample.xbrl", xml_content)
    zip_bytes = bio.getvalue()

    api_client = DummyAPIClient(zip_bytes)
    svc = EdinetDownloadService(api_client=api_client, work_dir=tmp_path)

    extracted = await svc.download_and_extract("DOC123")
    assert Path(extracted).exists()

    root = await svc.download_and_extract_root("DOC123")
    assert root.tag == "root"
    assert root.findtext("child") == "value"


@pytest.mark.asyncio
async def test_cleanup(tmp_path):
    file_path = tmp_path / "to_delete"
    file_path.mkdir()
    nested = file_path / "a.txt"
    nested.write_text("x")

    svc = EdinetDownloadService()
    svc.cleanup(file_path)
    assert not file_path.exists()
