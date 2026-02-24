"""Unit tests for BaseSaver implementations and helpers."""

import pytest

from app.services.data_synchronization._core.savers.base_saver import BaseSaver


class ConcreteSaver(BaseSaver[dict]):
    """Concrete saver used in tests."""

    def __init__(self):
        """Initialize internal storage for saved data."""
        self.saved_data = []

    async def save(self, data: dict, **kwargs) -> bool:
        """Save a single record or raise on error flag."""
        if data.get("error"):
            raise RuntimeError("Save failed")
        self.saved_data.append(data)
        return True

    async def save_batch(self, data_list: list[dict], **kwargs) -> int:
        """Save multiple records, skipping those that raise errors."""
        count = 0
        for data in data_list:
            try:
                if await self.save(data, **kwargs):
                    count += 1
            except RuntimeError:
                continue
        return count


class TestBaseSaver:
    """Tests for BaseSaver default behaviors."""

    @pytest.mark.asyncio
    async def test_save_success(self):
        """Saving a valid record updates internal state."""
        saver = ConcreteSaver()
        data = {"id": 1, "value": "test"}

        result = await saver.save(data)

        assert result is True
        assert len(saver.saved_data) == 1
        assert saver.saved_data[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_save_error(self):
        """Saving a record with error flag raises RuntimeError."""
        saver = ConcreteSaver()

        with pytest.raises(RuntimeError, match="Save failed"):
            await saver.save({"error": True})

    @pytest.mark.asyncio
    async def test_save_batch_success(self):
        """Batch save returns correct count for successful saves."""
        saver = ConcreteSaver()
        data_list = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3, "value": "c"},
        ]

        count = await saver.save_batch(data_list)

        assert count == 3
        assert len(saver.saved_data) == 3

    @pytest.mark.asyncio
    async def test_save_batch_with_errors(self):
        """Batch save skips entries that raise errors."""
        saver = ConcreteSaver()
        data_list = [
            {"id": 1, "value": "a"},
            {"error": True},
            {"id": 3, "value": "c"},
        ]

        count = await saver.save_batch(data_list)

        assert count == 2
        assert len(saver.saved_data) == 2

    @pytest.mark.asyncio
    async def test_validate_data(self):
        """validate_data returns True for dict and False for None."""
        saver = ConcreteSaver()

        res_valid = await saver.validate_data({"id": 1})
        res_none = await saver.validate_data(None)

        assert res_valid is True
        assert res_none is False

    @pytest.mark.asyncio
    async def test_prepare_for_save(self):
        """prepare_for_save returns dict for given mapping-like inputs."""
        saver = ConcreteSaver()

        data = {"id": 1, "value": "test"}

        result = await saver.prepare_for_save(data)

        assert result == {}

    @pytest.mark.asyncio
    async def test_handle_save_error(self):
        """Default handle_save_error does not re-raise exceptions."""
        saver = ConcreteSaver()

        await saver.handle_save_error({"id": 1}, RuntimeError("Test"))
