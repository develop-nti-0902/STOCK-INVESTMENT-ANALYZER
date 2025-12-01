"""
BaseFetcherの単体テスト
"""

import pytest

from app.services.core.fetchers.base_fetcher import BaseFetcher


class ConcreteFetcher(BaseFetcher[str]):
    """テスト用の具体的なFetcher実装"""

    async def fetch(self, identifier: str, **kwargs) -> str:
        """テスト用のfetch実装"""
        if identifier == "error":
            raise ValueError("Test error")
        return f"Data for {identifier}"

    async def fetch_batch(self, identifiers: list[str], **kwargs) -> list[str]:
        """テスト用のfetch_batch実装"""
        results = []
        for identifier in identifiers:
            try:
                data = await self.fetch(identifier, **kwargs)
                results.append(data)
            except ValueError:
                continue
        return results


class TestBaseFetcher:
    """BaseFetcherの単体テスト"""

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """正常なデータ取得のテスト"""
        fetcher = ConcreteFetcher()
        result = await fetcher.fetch("test_id")
        assert result == "Data for test_id"

    @pytest.mark.asyncio
    async def test_fetch_error(self):
        """エラー時の動作テスト"""
        fetcher = ConcreteFetcher()
        with pytest.raises(ValueError, match="Test error"):
            await fetcher.fetch("error")

    @pytest.mark.asyncio
    async def test_fetch_batch_success(self):
        """一括取得の正常動作テスト"""
        fetcher = ConcreteFetcher()
        results = await fetcher.fetch_batch(["id1", "id2", "id3"])
        assert len(results) == 3
        assert results[0] == "Data for id1"
        assert results[1] == "Data for id2"
        assert results[2] == "Data for id3"

    @pytest.mark.asyncio
    async def test_fetch_batch_with_errors(self):
        """一括取得時に一部エラーが発生する場合のテスト"""
        fetcher = ConcreteFetcher()
        results = await fetcher.fetch_batch(["id1", "error", "id3"])
        assert len(results) == 2  # errorは除外される
        assert results[0] == "Data for id1"
        assert results[1] == "Data for id3"

    @pytest.mark.asyncio
    async def test_validate_identifier(self):
        """識別子検証のテスト"""
        fetcher = ConcreteFetcher()

        assert await fetcher.validate_identifier("valid_id") is True
        assert await fetcher.validate_identifier("") is False
        assert await fetcher.validate_identifier(None) is False  # type: ignore

    @pytest.mark.asyncio
    async def test_handle_fetch_error(self):
        """エラーハンドリングのテスト"""
        fetcher = ConcreteFetcher()
        # デフォルトでは何もしない（例外を発生させない）
        await fetcher.handle_fetch_error("test_id", ValueError("Test"))
