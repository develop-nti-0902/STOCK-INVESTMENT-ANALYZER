"""Unit tests for EdinetProfitAndLossService behaviors."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.services.data_synchronization.market_data.edinet.profit_and_loss.service import (
    EdinetProfitAndLossService,
)


class _DummySaved:
    def __init__(self, id_, period_end_date):
        self.id = id_
        self.period_end_date = period_end_date


class _DummyFetcher:
    def __init__(self, path: Path | None = None, docs: list | None = None):
        self._path = path
        self._docs = docs or []

    async def fetch(self, doc_id: str):
        return self._path

    async def search_documents(self, current_date):
        return list(self._docs)


class _DummyParser:
    def __init__(self, parsed):
        self._parsed = parsed

    def parse(self, path: str):
        return self._parsed

    def parse_root(self, root, parsed_xbrl=None):
        return self._parsed


class _DummyConverter:
    def to_pydantic(self, data):
        class M:
            def __init__(self, period_end_date):
                self.period_end_date = period_end_date

        return M(data.get("period_end_date"))

    def from_pydantic(self, model):
        return {"period_end_date": model.period_end_date}


class _DummySaver:
    class _Repo:
        async def find_by_period(self, sec_code, period_end_date):
            return {"sec_code": sec_code, "period_end_date": period_end_date}

        async def find_by_fiscal_year(self, sec_code, fiscal_year):
            return {"sec_code": sec_code, "fiscal_year": fiscal_year}

        async def get_latest_by_sec_codes(self, sec_codes):
            return {s: {"sec_code": s, "id": i + 1} for i, s in enumerate(sec_codes)}

    def __init__(self):
        self.saved = []
        self.repository = self._Repo()

    async def save_single(self, data):
        obj = _DummySaved(id_=len(self.saved) + 1, period_end_date=data.get("period_end_date"))
        self.saved.append(obj)
        return obj

    async def get_latest_by_sec_code(self, sec_code: str):
        return None


class _DummyFileManager:
    def __init__(self):
        self.cleaned = False

    def cleanup(self, path: Path):
        self.cleaned = True

    def cleanup_old_files(self, directory: Path, max_age_hours: int = 24):
        return 0


class _Noop:
    pass


class _DummyDownloadService2:
    async def search_documents(self, current_date):
        return []

    async def download_and_extract(self, doc_id: str):
        return None

    def cleanup(self, path: Path):
        return None


class _DummyAsyncSession:
    """Minimal async session stub providing begin() and begin_nested() context managers."""

    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def begin(self):
        return _DummyAsyncSession._Ctx()

    def begin_nested(self):
        return _DummyAsyncSession._Ctx()


@pytest.mark.asyncio
async def test_process_document_success(tmp_path):
    """aggregate.process_document が正常に処理することを検証する."""
    extract_dir = tmp_path / "extracted" / "XBRL" / "PublicDoc"
    extract_dir.mkdir(parents=True)
    xbrl_file = extract_dir / "doc.xbrl"
    xbrl_file.write_text("<root/>", encoding="utf-8")

    parsed = {"current": {"period_end_date": "2024-03-31"}}

    parser = _DummyParser(parsed)
    converter = _DummyConverter()
    saver = _DummySaver()
    fm = _DummyFileManager()

    class _DummyDownloadService:
        def __init__(self, path: Path | None = None):
            self._path = path

        async def download_and_extract(self, doc_id: str):
            # return the actual xbrl file path so etree.parse can read it
            return self._path

        async def search_documents(self, current_date):
            return []

        def cleanup(self, path: Path):
            return None

    svc = EdinetProfitAndLossService(
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=fm,
        download_service=_DummyDownloadService(xbrl_file),
    )

    # use aggregate process_document
    summary = await svc._aggregate.process_document(
        doc_id="D1",
        transaction_atomic=False,
        sec_code="7203",
        submission_date="2025-01-01",
    )

    # expect at least one parser result marked ok and one saved record
    assert isinstance(summary, dict)
    assert any(r.get("status") == "ok" for r in summary.get("results", []))
    assert len(saver.saved) == 1


@pytest.mark.asyncio
async def test_get_by_period_and_annual_and_multiple_latest():
    """get_by_period, get_annual_data, get_multiple_latest の基本挙動を検証する."""
    parser = _Noop()
    converter = _Noop()
    saver = _DummySaver()
    fm = _Noop()

    class _DummyDownloadService2:
        async def search_documents(self, current_date):
            return []

        async def download_and_extract(self, doc_id: str):
            return None

        def cleanup(self, path: Path):
            return None

    svc = EdinetProfitAndLossService(
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=fm,
        download_service=_DummyDownloadService2(),
    )

    period = date(2024, 3, 31)
    r = await svc.get_by_period("7203", period)
    assert r["sec_code"] == "7203"
    assert r["period_end_date"] == period

    ar = await svc.get_annual_data("7203", 2024)
    assert ar["fiscal_year"] == 2024

    multi = await svc.get_multiple_latest(["A", "B"])
    assert "A" in multi and "B" in multi


@pytest.mark.asyncio
async def test__search_documents_filters(monkeypatch):
    """ダウンロードサービスの返す文書群をフィルタして処理することを検証する."""
    docs = [
        {"docTypeCode": "120", "secCode": "1001", "docDescription": "正常", "docID": "D1"},
        {"docTypeCode": "999", "secCode": "1002", "docDescription": "正常", "docID": "D2"},
        {"docTypeCode": "120", "secCode": None, "docDescription": "正常", "docID": "D3"},
        {"docTypeCode": "120", "secCode": "1003", "docDescription": "受益証券 関連", "docID": "D4"},
    ]

    parser = _Noop()
    converter = _Noop()
    saver = _DummySaver()
    fm = _Noop()

    class _DummyDownloadService3:
        def __init__(self, docs):
            self._docs = docs

        async def search_documents(self, current_date):
            return list(self._docs)

        async def download_and_extract(self, doc_id: str):
            return None

        def cleanup(self, path: Path):
            return None

    svc = EdinetProfitAndLossService(
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=fm,
        download_service=_DummyDownloadService3(docs),
    )

    async def fake_process_document(
        doc_id,
        session=None,
        transaction_atomic=True,
        sec_code=None,
        submission_date=None,
        filer_name=None,
    ):
        # return a success summary for docs with docID
        if doc_id:
            return {"doc_id": doc_id, "results": [{"status": "ok"}]}
        raise RuntimeError("fail")

    # ensure aggregate's download_service.search_documents returns our docs and stub process_document
    monkeypatch.setattr(
        svc._aggregate.download_service,
        "search_documents",
        svc._aggregate.download_service.search_documents,
        raising=False,
    )
    monkeypatch.setattr(svc._aggregate, "process_document", fake_process_document, raising=False)

    # provide a dummy async session because transaction_atomic=True requires a session
    session = _DummyAsyncSession()
    res = await svc._aggregate.process_date_range(
        date(2025, 1, 1), date(2025, 1, 1), session=session
    )
    # Only D1 should be processed successfully
    assert res["processed_documents"] == 1


@pytest.mark.asyncio
async def test_fetch_multiple_profit_and_losses_counts(monkeypatch):
    """複数文書の集計で成功・失敗数が正しく集計されることを検証する."""
    # setup service and monkeypatch _search_documents and process_document
    parser = _Noop()
    converter = _Noop()
    saver = _DummySaver()
    fm = _Noop()

    svc = EdinetProfitAndLossService(
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=fm,
        download_service=_DummyDownloadService2(),
    )

    docs = [
        {
            "docTypeCode": "120",
            "docID": "OK",
            "secCode": "A",
            "submitDateTime": "2025-01-02 00:00",
            "filerName": "F",
        },
        {
            "docTypeCode": "120",
            "docID": None,
            "secCode": "B",
            "submitDateTime": "2025-01-02 00:00",
            "filerName": "G",
        },
    ]

    async def fake_search(current_date):
        return docs

    async def fake_process_document(doc_id, sec_code, submission_date, filer_name=""):
        if doc_id == "OK":
            return [{"id": 1}]
        raise RuntimeError("fail")

    # Patch the aggregate's download_service.search_documents to our fake_search
    monkeypatch.setattr(
        svc._aggregate.download_service, "search_documents", fake_search, raising=False
    )

    # adapt fake_process_document to aggregate.process_document signature
    async def fake_agg_process_document(
        doc_id,
        session=None,
        transaction_atomic=True,
        sec_code=None,
        submission_date=None,
        filer_name=None,
    ):
        try:
            res = await fake_process_document(doc_id, sec_code, submission_date, filer_name)
            return {"doc_id": doc_id, "results": [{"status": "ok", "saved": res}]}
        except Exception:
            return {"doc_id": doc_id, "results": [{"status": "error"}]}

    monkeypatch.setattr(svc._aggregate, "process_document", fake_agg_process_document)

    session = _DummyAsyncSession()
    res = await svc._aggregate.process_date_range(
        date(2025, 1, 1), date(2025, 1, 1), session=session
    )
    assert res["processed_documents"] == 1
    assert res["failed_documents"] == 1
