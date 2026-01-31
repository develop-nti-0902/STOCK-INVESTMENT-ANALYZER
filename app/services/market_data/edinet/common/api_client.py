from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, cast

import aiohttp

from app.utils.config import get_settings


@dataclass
class EdinetAPIClient:
    # EDINET の実運用は v2 を利用する
    base_url: str = "https://disclosure.edinet-fsa.go.jp/api/v2"
    timeout: int = 10
    max_retries: int = 3

    async def _request_json(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Any:
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt < self.max_retries:
            attempt += 1
            close_session = False
            if session is None:
                session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
                close_session = True
            try:
                async with session.get(
                    f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                    params=params,
                    headers=headers,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                Exception,
            ) as exc:
                last_exc = exc
                await asyncio.sleep(0.5 * attempt)
                continue
            finally:
                if close_session:
                    await session.close()
        raise last_exc or RuntimeError("Unknown error in _request_json")

    async def _request_bytes(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> bytes:
        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt < self.max_retries:
            attempt += 1
            close_session = False
            if session is None:
                session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )
                close_session = True
            try:
                async with session.get(
                    f"{self.base_url.rstrip('/')}/{path.lstrip('/')}",
                    params=params,
                    headers=headers,
                ) as resp:
                    resp.raise_for_status()
                    return await resp.read()
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                Exception,
            ) as exc:
                last_exc = exc
                await asyncio.sleep(0.5 * attempt)
                continue
            finally:
                if close_session:
                    await session.close()
        raise last_exc or RuntimeError("Unknown error in _request_bytes")

    async def search_documents(
        self,
        target_date: date,
        doc_type: int = 2,
        headers: Optional[Dict[str, str]] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> List[Dict[str, Any]]:
        """指定日付に公開された文書を検索します。

        戻り値はパース済みのJSONリストです。リトライとタイムアウトを使用します。
        """
        params = {
            "date": target_date.isoformat(),
            "type": doc_type,
        }
        data = await self._request_json(
            "documents.json", params=params, headers=headers, session=session
        )
        # APIが'results'キーを返す場合や、直接リストを返す場合があるため、リストに正規化する
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        if isinstance(data, list):
            return data
        return []

    async def download_document(
        self,
        doc_id: str,
        doc_type: int = 1,
        subscription_key: Optional[str] = None,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> bytes:
        """文書IDでZIPをダウンロードし、生のバイト列を返します。

        実運用スクリプトに合わせ、`/documents/{doc_id}` エンドポイントを使用し、
        `type` パラメータや `Subscription-Key` を渡せるようにします。
        """
        path = f"documents/{doc_id}"
        params: Dict[str, Any] = {"type": doc_type}
        headers: Dict[str, str] = {}

        # subscription_key が渡されなかった場合は Settings から取得を試みる。
        # Settings の取得に失敗した場合は例外をそのまま伝播させる（明示的にエラーにする）。
        if not subscription_key:
            settings = (
                get_settings()
            )  # 失敗した場合は SettingsValidationError 等が発生して伝播する
            subscription_key = cast(
                Optional[str],
                getattr(settings, "EDINET_SUBSCRIPTION_KEY", None),
            )

        # Settings にキーが無ければ明示的にエラーとする（環境変数へのフォールバックは行わない）
        if not subscription_key:
            raise RuntimeError(
                "EDINET_SUBSCRIPTION_KEY is not set in settings"
            )

        if subscription_key:
            # EDINETのサンプルではクエリパラメータに含めている場合があるが、
            # ヘッダとして渡すこともあるため両方に対応できるようにする
            params["Subscription-Key"] = subscription_key
            headers["Subscription-Key"] = subscription_key

        return await self._request_bytes(
            path, params=params, headers=headers, session=session
        )
