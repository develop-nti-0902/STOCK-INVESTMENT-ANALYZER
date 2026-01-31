from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

import pytest

from app.services.market_data.edinet.balance_sheet.service import (
    EdinetBalanceSheetService,
)


class DummyFetcher:
    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path

    async def fetch(self, identifier: str) -> Path:
        # create a dummy file and return its path
        p = self.tmp_path / f"{identifier}.xbrl"
        p.write_text("<root/>", encoding="utf-8")
        return p


class DummyParser:
    def parse(self, _data):
        return {
            "current": {
                "assets": 1000.0,
                "liabilities": 200.0,
                "equity": 800.0,
                "period_end": "2025-03-31",
                "consolidation": True,
            }
        }


class DummyFileManager:
    def __init__(self):
        self.cleaned = False

    def cleanup(self, path: Path) -> None:
        self.cleaned = True


class DummyRepo:
    def __init__(self, session):
        self.session = session

    async def upsert(self, data: dict):
        return {"upserted": data}


@pytest.mark.asyncio
async def test_fetch_and_save_single_success(tmp_path):
    fetcher = DummyFetcher(tmp_path)
    parser = DummyParser()
    fm = DummyFileManager()

    @asynccontextmanager
    async def session_maker():
        class DummySession:
            async def commit(self):
                return None

            async def rollback(self):
                return None

            async def close(self):
                return None

        yield DummySession()

    service = EdinetBalanceSheetService(
        fetcher=fetcher,
        parser=parser,
        file_manager=fm,
        session_maker=session_maker,
        repo_class=DummyRepo,
    )

    res = await service.fetch_and_save_single(
        doc_id="DOC123",
        sec_code="7203",
        submission_date=date(2025, 4, 1),
        filer_name="DummyFiler",
    )

    assert isinstance(res, dict)
    assert res["upserted"]["doc_id"] == "DOC123"
    assert fm.cleaned is True
