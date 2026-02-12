"""EDINET 貸借対照表サービスのユニットテスト."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.services.market_data.edinet.balance_sheet.service import EdinetBalanceSheetService
from app.services.market_data.edinet.download_service import EdinetDownloadService


class DummyFetcher:
    """ダミーのフェッチャ."""

    def __init__(self, tmp_path: Path):
        """初期化."""
        self.tmp_path = tmp_path

    async def fetch(self, identifier: str) -> Path:
        """ダミーのXBRLファイルを作成して返す."""
        p = self.tmp_path / f"{identifier}.xbrl"
        p.write_text("<root/>", encoding="utf-8")
        return p


class DummyParser:
    """ダミーのパーサ."""

    def parse(self, _data):
        """ダミーのパース結果を返す."""
        return {
            "current": {
                "assets": 1000.0,
                "liabilities": 200.0,
                "equity": 800.0,
                "period_end": date(2025, 3, 31),
                "consolidation": True,
            }
        }

    def parse_root(self, root):
        """互換のため root を受け取る parse_root を提供する（テスト用）。"""
        return self.parse(root)

    def parse_root(self, root, parsed_xbrl=None):
        """互換のため root と parsed_xbrl を受け取る parse_root を提供する（テスト用）。"""
        return self.parse(root)


class DummyConverter:
    """ダミーのコンバータ."""

    def to_pydantic(self, data):
        """ダミーの Pydantic モデルを返す."""
        return {
            "doc_id": data.get("doc_id", ""),
            "sec_code": data.get("sec_code", ""),
            "filer_name": data.get("filer_name"),
            "submission_date": data.get("submission_date"),
            "period_end_date": data.get("period_end"),
            "fiscal_year": 2025,
            "report_type": "annual",
            "total_assets": data.get("assets"),
            "total_liabilities": data.get("liabilities"),
            "total_equity": data.get("equity"),
            "is_consolidated": data.get("consolidation"),
        }

    def from_pydantic(self, model):
        """モデルをそのまま返す."""
        return model


class DummySaver:
    """ダミーのセーバー."""

    def __init__(self):
        """初期化."""
        self.saved_records = []
        self.repository = DummyRepository()

    async def save_single(self, data: dict):
        """ダミーの保存処理."""
        self.saved_records.append(data)
        return {"saved": data}

    async def save(self, data: dict):
        """互換のため `save` メソッドを提供するラッパー（aggregate 互換）。"""
        return await self.save_single(data)


class DummyRepository:
    """ダミーのリポジトリ."""

    async def find_latest_by_sec_code(self, sec_code: str):
        """ダミーの検索結果を返す."""
        return None


class DummyFileManager:
    """ダミーのファイルマネージャー."""

    def __init__(self):
        """初期化."""
        self.cleaned = False

    def cleanup(self, path: Path) -> None:
        """クリーンアップ処理."""
        self.cleaned = True


@pytest.mark.asyncio
async def test_fetch_and_save_success(tmp_path):
    """fetch_and_save が正常に動作することを確認するテスト."""
    fetcher = DummyFetcher(tmp_path)
    parser = DummyParser()
    converter = DummyConverter()
    saver = DummySaver()
    fm = DummyFileManager()

    class _DummyDownloadService:
        def __init__(self, fetcher: DummyFetcher):
            self._fetcher = fetcher
            self.work_dir = getattr(fetcher, "tmp_path", None)

        async def download_and_extract(self, identifier: str):
            return await self._fetcher.fetch(identifier)

        async def search_documents(self, current_date):
            return []

        def cleanup(self, path: Path) -> None:
            return None

    service = EdinetBalanceSheetService(
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=fm,
        download_service=_DummyDownloadService(fetcher),
    )

    # call aggregate update service for a single document
    summary = await service._aggregate.process_document(
        doc_id="DOC123",
        transaction_atomic=False,
        sec_code="7203",
        submission_date=date(2025, 4, 1),
        filer_name="DummyFiler",
    )

    # サマリ形式で結果が返る（parser ごとの結果リスト）
    assert isinstance(summary, dict)
    assert summary.get("doc_id") == "DOC123"
    assert isinstance(summary.get("results"), list)
    # saver によって 1 件保存されていること
    assert len(saver.saved_records) == 1
