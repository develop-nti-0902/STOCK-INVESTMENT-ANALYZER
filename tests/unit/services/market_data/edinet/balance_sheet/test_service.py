"""EDINET 貸借対照表サービスのユニットテスト."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.services.market_data.edinet.balance_sheet.service import EdinetBalanceSheetService


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

    service = EdinetBalanceSheetService(
        fetcher=fetcher,
        parser=parser,
        converter=converter,
        saver=saver,
        file_manager=fm,
    )

    res = await service.fetch_and_save(
        doc_id="DOC123",
        sec_code="7203",
        submission_date=date(2025, 4, 1),
        filer_name="DummyFiler",
    )

    # サービスは保存の結果リストを返す
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0]["saved"]["doc_id"] == "DOC123"
    assert fm.cleaned is True
    assert len(saver.saved_records) == 1
