"""EDINET 文書のダウンロード・解凍・一度だけのパースを扱うユーティリティモジュール.

軽量ラッパーとして API クライアントからバイト列を受け取り、展開・パース・一時ファイル管理を行います。
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, Optional

from lxml import etree

from app.services.data_synchronization.market_data.edinet.common.api_client import EdinetAPIClient

logger = logging.getLogger(__name__)


class EdinetDownloadService:
    """ダウンロード／解凍／一度だけのパースを統括するサービス.

    - `download_and_extract` は抽出先の `Path` を返す。
    - `download_and_extract_root` は `lxml.etree._Element`（パース済 root）を返す。
    - `cleanup` は抽出先ディレクトリを削除する（例外はログに記録）。
    """

    def __init__(
        self, api_client: Optional[EdinetAPIClient] = None, work_dir: Optional[Path] = None
    ) -> None:
        """インスタンス初期化.

        テストや既存のフェッチャ互換のため `api_client` と `work_dir` は外部注入可能とする。
        """
        # API クライアント / 作業ディレクトリを受け取る（テストや既存の fetcher 互換性用）
        self.api_client: EdinetAPIClient = api_client or EdinetAPIClient()
        self.work_dir: Path = work_dir or Path("work/edinet_temp")
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def download_and_extract(self, doc_id: str) -> Path:
        """ダウンロードして解凍した XBRL ファイル/ディレクトリのパスを返す.

        呼び出しは非同期。内部では既存の `EdinetDocumentFetcher.fetch` を使用する。
        """
        # download bytes via api_client and extract
        data = await self.api_client.download_document(doc_id)

        def _sync_write_extract() -> Path:
            tmpdir = Path(tempfile.mkdtemp(prefix=f"edinet_{doc_id}_", dir=self.work_dir))
            zip_path = tmpdir / f"{doc_id}.zip"
            with open(zip_path, "wb") as f:
                f.write(data)
            # extract
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)
            # locate xbrl file under XBRL/PublicDoc (財務諸表本体)
            public_doc_paths = list(tmpdir.glob("**/PublicDoc/**/*.xbrl"))
            if public_doc_paths:
                for p in public_doc_paths:
                    if "AuditDoc" not in str(p):
                        return p
                return public_doc_paths[0]
            for p in tmpdir.rglob("*.xbrl"):
                return p
            for p in tmpdir.rglob("*.xml"):
                return p
            for p in tmpdir.rglob("*.htm"):
                return p
            raise FileNotFoundError("No XBRL file found in archive")

        path = await asyncio.to_thread(_sync_write_extract)
        return path

    async def download_and_extract_root(self, doc_id: str) -> etree._Element:
        """ダウンロード→解凍→lxmlでパースして root を返す.

        パースはブロッキングなので `asyncio.to_thread` で実行する。
        """
        extracted_path = await self.download_and_extract(doc_id)

        def _parse() -> etree._Element:
            parser = etree.parse(str(extracted_path))
            return parser.getroot()

        root = await asyncio.to_thread(_parse)
        return root

    def cleanup(self, path: Path) -> None:
        """抽出ディレクトリ（またはファイル）を削除する。失敗しても例外は投げずログのみ出す."""
        try:
            if not path.exists():
                return
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("抽出成果物のクリーンアップに失敗しました %s: %s", path, exc)

    async def search_documents(self, target_date: "date") -> list[dict[str, Any]]:
        """指定日付の書類を検索してメタ情報リストを返す."""
        return await self.api_client.search_documents(target_date)
