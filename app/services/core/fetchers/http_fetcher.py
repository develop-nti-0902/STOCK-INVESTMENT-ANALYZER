"""HTTP 通信共通処理クラス.

`aiohttp` を用いた HTTP 通信の共通処理を提供します（セッション管理、
タイムアウト、簡易レート制御など）。

仕様書: docs/architecture/layers/service_layer.md 3.1章
"""

import asyncio
from typing import Any, Optional

import aiohttp
from aiohttp import ClientTimeout

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HttpFetcher:
    """HTTP 通信の共通処理クラス.

    Attributes:
        timeout: リクエストタイムアウト設定
        semaphore: 並列リクエスト数制限用セマフォ
        rate_limit_delay: レート制限時の待機時間（秒）
    """

    def __init__(self) -> None:
        """HttpFetcherを初期化します。"""
        config = get_settings()

        # タイムアウト設定
        self.timeout = ClientTimeout(
            total=config.YAHOO_FINANCE_TIMEOUT,
            connect=config.YAHOO_FINANCE_TIMEOUT * 0.3,
        )

        # 並列処理数制限
        concurrency_limit = config.YAHOO_FINANCE_CONCURRENCY_LIMIT
        self.semaphore = asyncio.Semaphore(concurrency_limit)

        # レート制限設定
        backoff = config.YAHOO_FINANCE_RETRY_BACKOFF
        self.rate_limit_delay = backoff * 0.1

        # セッションはasync context managerで管理
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "HttpFetcher":
        """非同期コンテキストマネージャ開始処理.

        Returns:
            HttpFetcher: 自インスタンス
        """
        await self._ensure_session()
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        """非同期コンテキストマネージャ終了処理.

        Args:
            exc_type: 発生した例外の型
            exc_val: 発生した例外インスタンス
            exc_tb: トレースバック
        """
        await self.close()

    async def _ensure_session(self) -> None:
        """ClientSession が未作成またはクローズされている場合に作成する."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        """保持する ClientSession を安全にクローズする."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get(
        self,
        url: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """
        GETリクエストを実行します。

        Args:
            url: リクエストURL
            params: クエリパラメータ
            headers: リクエストヘッダー
            **kwargs: aiohttp.ClientSession.get()の追加引数

        Returns:
            aiohttp.ClientResponse: レスポンスオブジェクト

        Raises:
            aiohttp.ClientError: HTTP通信エラー
            asyncio.TimeoutError: タイムアウト
        """
        await self._ensure_session()
        assert self._session is not None

        async with self.semaphore:
            logger.debug("GET request to %s with params %s", url, params)

            # レート制限対応
            await asyncio.sleep(self.rate_limit_delay)

            try:
                response = await self._session.get(
                    url=url, params=params, headers=headers, **kwargs
                )
                response.raise_for_status()
                return response

            except aiohttp.ClientError as e:
                logger.error("HTTP request failed for %s: %s", url, e)
                raise
            except asyncio.TimeoutError as e:
                logger.error("Request timeout for %s: %s", url, e)
                raise

    async def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs: Any
    ) -> aiohttp.ClientResponse:
        """
        POSTリクエストを実行します。

        Args:
            url: リクエストURL
            data: POSTデータ
            json: JSONデータ
            headers: リクエストヘッダー
            **kwargs: aiohttp.ClientSession.post()の追加引数

        Returns:
            aiohttp.ClientResponse: レスポンスオブジェクト

        Raises:
            aiohttp.ClientError: HTTP通信エラー
            asyncio.TimeoutError: タイムアウト
        """
        await self._ensure_session()
        assert self._session is not None

        async with self.semaphore:
            logger.debug("POST request to %s", url)

            # レート制限対応
            await asyncio.sleep(self.rate_limit_delay)

            try:
                response = await self._session.post(
                    url=url, data=data, json=json, headers=headers, **kwargs
                )
                response.raise_for_status()
                return response

            except aiohttp.ClientError as e:
                logger.error("HTTP request failed for %s: %s", url, e)
                raise
            except asyncio.TimeoutError as e:
                logger.error("Request timeout for %s: %s", url, e)
                raise

    def update_timeout(self, timeout_seconds: float) -> None:
        """
        タイムアウト設定を更新します。

        Args:
            timeout_seconds: 新しいタイムアウト時間（秒）
        """
        self.timeout = ClientTimeout(
            total=timeout_seconds,
            connect=min(timeout_seconds * 0.3, 10.0),
        )

    def update_rate_limit(self, delay_seconds: float) -> None:
        """
        レート制限の遅延時間を更新します。

        Args:
            delay_seconds: リクエスト間の待機時間（秒）
        """
        self.rate_limit_delay = delay_seconds
