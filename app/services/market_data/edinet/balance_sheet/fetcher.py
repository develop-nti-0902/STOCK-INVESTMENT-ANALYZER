from __future__ import annotations

import asyncio
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.core.fetchers.base_fetcher import BaseFetcher
from app.services.market_data.edinet.common.api_client import EdinetAPIClient


@dataclass
class EdinetDocumentFetcher(BaseFetcher[Path]):
    api_client: EdinetAPIClient
    work_dir: Path = Path("work/edinet_temp")

    def __post_init__(self) -> None:
        self.work_dir.mkdir(parents=True, exist_ok=True)

    async def validate_identifier(self, identifier: str) -> bool:
        if not await super().validate_identifier(identifier):
            return False
        # EDINET の doc_id は英数字で構成されることが多いので簡易チェック
        return isinstance(identifier, str) and len(identifier) > 0

    async def download_document(self, identifier: str) -> bytes:
        return await self.api_client.download_document(identifier)

    async def _write_and_extract(self, identifier: str, data: bytes) -> Path:
        def _sync_write_extract() -> Path:
            tmpdir = Path(
                tempfile.mkdtemp(
                    prefix=f"edinet_{identifier}_", dir=self.work_dir
                )
            )
            zip_path = tmpdir / f"{identifier}.zip"
            with open(zip_path, "wb") as f:
                f.write(data)
            # extract
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)
            # locate xbrl file under XBRL/PublicDoc (財務諸表本体)
            public_doc_paths = list(tmpdir.glob("**/PublicDoc/**/*.xbrl"))
            if public_doc_paths:
                # PublicDocディレクトリ内のXBRLファイルを優先
                # ファイル名に "BalanceSheet" や "jpcrp" が含まれるものを優先
                for p in public_doc_paths:
                    # 監査報告書（AuditDoc）を除外
                    if "AuditDoc" not in str(p):
                        return p
                # フォールバック: PublicDoc内の最初のXBRL
                return public_doc_paths[0]
            # fallback: any xbrl file
            for p in tmpdir.rglob("*.xbrl"):
                return p
            # fallback: any xml or htm
            for p in tmpdir.rglob("*.xml"):
                return p
            for p in tmpdir.rglob("*.htm"):
                return p
            raise FileNotFoundError("No XBRL file found in archive")

        return await asyncio.to_thread(_sync_write_extract)

    async def fetch(self, identifier: str, **kwargs: Any) -> Path:
        if not await self.validate_identifier(identifier):
            raise ValueError("Invalid identifier")
        data = await self.download_document(identifier)
        xbrl_path = await self._write_and_extract(identifier, data)
        return xbrl_path

    async def fetch_batch(
        self, identifiers: List[str], **kwargs: Any
    ) -> List[Path]:
        """複数文書を並列取得して取得に成功したもののパス一覧を返す。

        並列度は `concurrency` キーワード引数で指定可能（デフォルト 5）。
        失敗した文書はログを残して結果から除外する。
        """
        concurrency: int = int(kwargs.get("concurrency", 5))
        sem = asyncio.Semaphore(concurrency)

        async def _worker(doc_id: str) -> Optional[Path]:
            async with sem:
                try:
                    return await self.fetch(doc_id, **kwargs)
                except Exception:
                    await self.handle_fetch_error(
                        doc_id, Exception("fetch failed")
                    )
                    return None

        tasks = [asyncio.create_task(_worker(i)) for i in identifiers]
        results = await asyncio.gather(*tasks)
        # mypy のため Optional を除去して List[Path] を返す
        return [r for r in results if r is not None]

    async def search_documents(
        self, target_date: date, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        return await self.api_client.search_documents(target_date)
