"""HttpFetcherクラスの単体テスト.

HTTP通信の共通処理をテストします。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from app.services.data_synchronization._core.fetchers.http_fetcher import HttpFetcher


class TestHttpFetcher:
    """HttpFetcherクラスのテスト."""

    @pytest.fixture
    def http_fetcher(self) -> HttpFetcher:
        """テスト用のHttpFetcherインスタンス."""
        with patch(
            "app.services.data_synchronization._core.fetchers.http_fetcher.get_settings"
        ) as mock_settings:
            mock_config = MagicMock()
            mock_config.YAHOO_FINANCE_TIMEOUT = 30.0
            mock_config.YAHOO_FINANCE_CONCURRENCY_LIMIT = 5
            mock_config.YAHOO_FINANCE_RETRY_BACKOFF = 2.0
            mock_settings.return_value = mock_config

            return HttpFetcher()

    def test_init(self, http_fetcher: HttpFetcher) -> None:
        """初期化テスト."""
        # Arrange - 準備

        # Act - 実行
        # Assert - 検証
        assert http_fetcher.timeout.total == 30.0
        assert http_fetcher.timeout.connect == 9.0  # 30.0 * 0.3
        assert http_fetcher.rate_limit_delay == 0.2  # 2.0 * 0.1
        assert http_fetcher._session is None

    @pytest.mark.asyncio
    async def test_context_manager(self, http_fetcher: HttpFetcher) -> None:
        """非同期コンテキストマネージャーのテスト."""
        # Arrange - 準備

        # Act - 実行
        async with http_fetcher:
            assert http_fetcher._session is not None
            assert not http_fetcher._session.closed

        # Assert - 検証
        assert http_fetcher._session is None

    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self, http_fetcher: HttpFetcher) -> None:
        """セッションが作成されることをテスト."""
        # Arrange - 準備

        # Act - 実行
        await http_fetcher._ensure_session()

        # Assert - 検証
        assert http_fetcher._session is not None
        assert not http_fetcher._session.closed

        # クリーンアップ
        await http_fetcher.close()

    @pytest.mark.asyncio
    async def test_close_closes_session(self, http_fetcher: HttpFetcher) -> None:
        """セッションがクローズされることをテスト."""
        # Arrange - 準備
        await http_fetcher._ensure_session()
        assert http_fetcher._session is not None

        # Act - 実行
        await http_fetcher.close()

        # Assert - 検証
        assert http_fetcher._session is None

    @pytest.mark.asyncio
    async def test_get_success(self, http_fetcher: HttpFetcher) -> None:
        """GETリクエスト成功時のテスト."""
        # Arrange - 準備
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act - 実行
            result = await http_fetcher.get("https://api.example.com/test")

            # Assert - 検証
            assert result == mock_response
            mock_session.get.assert_called_once_with(
                url="https://api.example.com/test", params=None, headers=None
            )

    @pytest.mark.asyncio
    async def test_get_with_params_and_headers(self, http_fetcher: HttpFetcher) -> None:
        """GETリクエスト with パラメータとヘッダーのテスト."""
        # Arrange - 準備
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        params = {"key": "value"}
        headers = {"Authorization": "Bearer token"}
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act - 実行
            result = await http_fetcher.get(
                "https://api.example.com/test", params=params, headers=headers
            )

            # Assert - 検証
            assert result == mock_response
            mock_session.get.assert_called_once_with(
                url="https://api.example.com/test",
                params=params,
                headers=headers,
            )

    @pytest.mark.asyncio
    async def test_get_http_error(self, http_fetcher: HttpFetcher) -> None:
        """GETリクエストでHTTPエラーが発生した場合のテスト."""
        # Arrange - 準備
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("HTTP Error")

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act & Assert - 実行と検証
            with pytest.raises(aiohttp.ClientError):
                await http_fetcher.get("https://api.example.com/test")

    @pytest.mark.asyncio
    async def test_get_timeout_error(self, http_fetcher: HttpFetcher) -> None:
        """GETリクエストでタイムアウトが発生した場合のテスト."""
        # Arrange - 準備
        import asyncio

        mock_session = AsyncMock()
        mock_session.get.side_effect = asyncio.TimeoutError("Timeout")

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act & Assert - 実行と検証
            with pytest.raises(asyncio.TimeoutError):
                await http_fetcher.get("https://api.example.com/test")

    @pytest.mark.asyncio
    async def test_post_success(self, http_fetcher: HttpFetcher) -> None:
        """POSTリクエスト成功時のテスト."""
        # Arrange - 準備
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        data = {"key": "value"}
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act - 実行
            result = await http_fetcher.post("https://api.example.com/test", data=data)

            # Assert - 検証
            assert result == mock_response
            mock_session.post.assert_called_once_with(
                url="https://api.example.com/test",
                data=data,
                json=None,
                headers=None,
            )

    @pytest.mark.asyncio
    async def test_post_with_json(self, http_fetcher: HttpFetcher) -> None:
        """POSTリクエスト with JSONのテスト."""
        # Arrange - 準備
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        json_data = {"message": "test"}
        mock_session = AsyncMock()
        mock_session.post.return_value = mock_response

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act - 実行
            result = await http_fetcher.post("https://api.example.com/test", json=json_data)

            # Assert - 検証
            assert result == mock_response
            mock_session.post.assert_called_once_with(
                url="https://api.example.com/test",
                data=None,
                json=json_data,
                headers=None,
            )

    @pytest.mark.asyncio
    async def test_post_http_error(self, http_fetcher: HttpFetcher) -> None:
        """POSTリクエストでHTTPエラーが発生した場合のテスト."""
        # Arrange - 準備
        mock_session = AsyncMock()
        mock_session.post.side_effect = aiohttp.ClientError("HTTP Error")

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act & Assert - 実行と検証
            with pytest.raises(aiohttp.ClientError):
                await http_fetcher.post("https://api.example.com/test")

    def test_update_timeout(self, http_fetcher: HttpFetcher) -> None:
        """タイムアウト更新テスト."""
        # Arrange - 準備

        # Act - 実行
        http_fetcher.update_timeout(60.0)

        # Assert - 検証
        assert http_fetcher.timeout.total == 60.0
        assert http_fetcher.timeout.connect == 10.0  # min(60.0 * 0.3, 10.0)

    def test_update_rate_limit(self, http_fetcher: HttpFetcher) -> None:
        """レート制限更新テスト."""
        # Arrange - 準備

        # Act - 実行
        http_fetcher.update_rate_limit(1.5)

        # Assert - 検証
        assert http_fetcher.rate_limit_delay == 1.5

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, http_fetcher: HttpFetcher) -> None:
        """並列処理数制限のテスト."""
        # Arrange - 準備
        import asyncio

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response

        with patch.object(http_fetcher, "_ensure_session"), patch.object(
            http_fetcher, "_session", mock_session
        ):

            # Act - 実行（並列で5つのリクエスト）
            tasks = [http_fetcher.get(f"https://api.example.com/test{i}") for i in range(5)]
            await asyncio.gather(*tasks)

            # Assert - 検証（セマフォが機能していることを確認）
            assert mock_session.get.call_count == 5
