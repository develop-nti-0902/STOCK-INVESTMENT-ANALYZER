import asyncio
from datetime import date

import pytest
from lxml import etree

from app.services.market_data.edinet.update_service import EdinetAggregateUpdateService


class DummyDownloadService:
    def __init__(self, path):
        self._path = path

    async def download_and_extract(self, doc_id: str):
        await asyncio.sleep(0)
        return self._path

    def cleanup(self, path):
        # no-op for test
        return None


@pytest.mark.asyncio
async def test_process_document_non_atomic(tmp_path):
    # prepare a minimal xbrl file
    xml = b"<root><d>1</d></root>"
    p = tmp_path / "s.xbrl"
    p.write_bytes(xml)

    def parser_callable(root):
        # root may be etree.Element or path string depending on code path
        if isinstance(root, etree._Element):
            return {"a": 1}
        return {"a": 1}

    async def saver_callable(parsed):
        await asyncio.sleep(0)
        return {"saved": True}

    class DummyConverter:
        def to_pydantic(self, data):
            return data

        def from_pydantic(self, model):
            return model

    ds = DummyDownloadService(str(p))
    svc = EdinetAggregateUpdateService(
        download_service=ds,
        parser_saver_pairs=[(parser_callable, DummyConverter(), saver_callable)],
    )

    summary = await svc.process_document("doc1", transaction_atomic=False)
    assert summary["doc_id"] == "doc1"
    assert len(summary["results"]) == 1
    assert summary["results"][0]["status"] == "ok"


@pytest.mark.asyncio
async def test_process_date_range_single_day(tmp_path):
    # prepare a minimal xbrl file
    xml = b"<root><d>1</d></root>"
    p = tmp_path / "s.xbrl"
    p.write_bytes(xml)

    def parser_callable(root):
        return {"a": 1}

    async def saver_callable(parsed):
        await asyncio.sleep(0)
        return {"saved": True}

    class DummyConverter:
        def to_pydantic(self, data):
            return data

        def from_pydantic(self, model):
            return model

    class DummyFetcher:
        async def search_documents(self, current_date):
            await asyncio.sleep(0)
            return [
                {
                    "docID": "doc1",
                    "docTypeCode": "120",
                    "secCode": "7203",
                    "docDescription": "年次報告",
                }
            ]

    ds = DummyDownloadService(str(p))
    ds.fetcher = DummyFetcher()
    # adapt legacy tests which set `fetcher` — provide `search_documents` on the download service
    ds.search_documents = ds.fetcher.search_documents

    svc = EdinetAggregateUpdateService(
        download_service=ds,
        parser_saver_pairs=[(parser_callable, DummyConverter(), saver_callable)],
    )

    summary = await svc.process_date_range(
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 1),
        transaction_atomic=False,
    )

    assert summary["total_documents"] == 1
    assert summary["processed_documents"] == 1
    assert summary["saved_items"] == 1
    assert summary["failed_documents"] == 0
