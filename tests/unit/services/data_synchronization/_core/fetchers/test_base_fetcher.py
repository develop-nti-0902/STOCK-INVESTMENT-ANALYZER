"""Unit tests for BaseFetcher implementations and helpers."""

import pytest

from app.services.data_synchronization._core.fetchers.base_fetcher import BaseFetcher


class ConcreteFetcher(BaseFetcher[str]):
    """Concrete fetcher used in tests."""

    async def fetch(self, identifier: str, **kwargs) -> str:
        """Fetch a single identifier or raise on 'error'."""
        if identifier == "error":
            raise ValueError("Test error")
        return f"Data for {identifier}"

    async def fetch_batch(self, identifiers: list[str], **kwargs) -> list[str]:
        """Fetch multiple identifiers, skipping those that error."""
        results = []
        for identifier in identifiers:
            try:
                data = await self.fetch(identifier, **kwargs)
                results.append(data)
            except ValueError:
                continue
        return results


class TestBaseFetcher:
    """Tests for BaseFetcher behavior and error handling."""

    @pytest.mark.asyncio
    async def test_fetch_success(self):
        """Fetch returns expected data for valid identifier."""
        # Arrange: テスト用のFetcherを準備
        fetcher = ConcreteFetcher()

        # Act: 正常にfetchできることを確認
        result = await fetcher.fetch("test_id")

        # Assert: 取得結果が期待通りであることを検証
        assert result == "Data for test_id"

    @pytest.mark.asyncio
    async def test_fetch_error(self):
        """Fetch raises ValueError for error identifier."""
        # Arrange: テスト用のFetcherを準備
        fetcher = ConcreteFetcher()

        # Act / Assert: エラーが発生することを確認
        with pytest.raises(ValueError, match="Test error"):
            await fetcher.fetch("error")

    @pytest.mark.asyncio
    async def test_fetch_batch_success(self):
        """Fetch batch returns correct list for identifiers."""
        # Arrange: テスト用のFetcherと識別子リストを準備
        fetcher = ConcreteFetcher()
        identifiers = ["id1", "id2", "id3"]

        # Act: 複数取得を実行
        results = await fetcher.fetch_batch(identifiers)

        # Assert: 取得結果が期待通りであることを検証
        assert len(results) == 3
        assert results[0] == "Data for id1"
        assert results[1] == "Data for id2"
        assert results[2] == "Data for id3"

    @pytest.mark.asyncio
    async def test_fetch_batch_with_errors(self):
        """Fetch batch skips identifiers that raise errors."""
        # Arrange: テスト用のFetcherと識別子リスト（途中にエラーを含む）を準備
        fetcher = ConcreteFetcher()
        identifiers = ["id1", "error", "id3"]

        # Act: 一括取得を実行（エラーはスキップされる想定）
        results = await fetcher.fetch_batch(identifiers)

        # Assert: エラー要素が除外されていることを検証
        assert len(results) == 2  # errorは除外される
        assert results[0] == "Data for id1"
        assert results[1] == "Data for id3"

    @pytest.mark.asyncio
    async def test_validate_identifier(self):
        """Validate identifier handling for various inputs."""
        # Arrange: テスト用のFetcherを準備
        fetcher = ConcreteFetcher()

        # Act: 複数の入力に対して検証を実行
        res_valid = await fetcher.validate_identifier("valid_id")
        res_empty = await fetcher.validate_identifier("")
        res_none = await fetcher.validate_identifier(None)  # type: ignore

        # Assert: 各ケースの期待結果を検証
        assert res_valid is True
        assert res_empty is False
        assert res_none is False

    @pytest.mark.asyncio
    async def test_handle_fetch_error(self):
        """Ensure default error handler does not re-raise."""
        # Arrange: テスト用のFetcherを準備
        fetcher = ConcreteFetcher()

        # Act / Assert: デフォルト実装では例外が再送出されないことを確認
        await fetcher.handle_fetch_error("test_id", ValueError("Test"))
