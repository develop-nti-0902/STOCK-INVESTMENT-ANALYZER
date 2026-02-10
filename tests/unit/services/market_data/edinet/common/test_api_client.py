"""Edinet API クライアントのユニットテスト（モックを使った非同期テスト）."""

import os
from datetime import date

import pytest

from app.services.market_data.edinet.common.api_client import EdinetAPIClient

# テスト実行時に Settings が EDINET_SUBSCRIPTION_KEY を要求するため、ダミー値を設定
os.environ.setdefault("EDINET_SUBSCRIPTION_KEY", "dummy_key")


class _MockResponse:
    def __init__(self, json_data=None, bytes_data: bytes = b"", status: int = 200):
        self._json = json_data
        self._bytes = bytes_data
        self.status = status

    async def json(self):
        return self._json

    async def read(self):
        return self._bytes

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class _MockContext:
    def __init__(self, response: _MockResponse):
        self._resp = response

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _MockSession:
    def __init__(self, response: _MockResponse):
        self._response = response

    def get(self, *args, **kwargs):
        return _MockContext(self._response)

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_search_documents_returns_list():
    """search_documents が結果のリストを返すことを確認する."""
    data = {"results": [{"docID": "A1"}, {"docID": "A2"}]}
    resp = _MockResponse(json_data=data, status=200)
    session = _MockSession(resp)
    client = EdinetAPIClient()
    results = await client.search_documents(date(2025, 1, 1), session=session)
    assert isinstance(results, list)
    assert results[0]["docID"] == "A1"


@pytest.mark.asyncio
async def test_download_document_returns_bytes():
    """download_document がバイト列を返すことを確認する."""
    content = b"PDFDATA"
    resp = _MockResponse(bytes_data=content, status=200)
    session = _MockSession(resp)
    client = EdinetAPIClient()
    out = await client.download_document("DOCID123", session=session)
    assert out == content


@pytest.mark.asyncio
async def test_retry_on_failure_then_success():
    """最初の失敗の後に再試行が成功する振る舞いを確認する."""
    # first response fails, second succeeds
    resp_fail = _MockResponse(status=500)
    resp_ok = _MockResponse(json_data={"results": [{"docID": "OK"}]}, status=200)

    class SessionSequence:
        def __init__(self):
            self.calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return _MockContext(resp_fail)
            return _MockContext(resp_ok)

        async def close(self):
            return None

    session = SessionSequence()
    client = EdinetAPIClient()
    results = await client.search_documents(date(2025, 1, 1), session=session)
    assert results[0]["docID"] == "OK"
