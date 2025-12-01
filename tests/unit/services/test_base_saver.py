"""
BaseSaverの単体テスト
"""

import pytest

from app.services.core.savers.base_saver import BaseSaver


class ConcreteSaver(BaseSaver[dict]):
    """テスト用の具体的なSaver実装"""

    def __init__(self):
        self.saved_data = []

    async def save(self, data: dict, **kwargs) -> bool:
        """テスト用のsave実装"""
        if data.get("error"):
            raise RuntimeError("Save failed")
        self.saved_data.append(data)
        return True

    async def save_batch(self, data_list: list[dict], **kwargs) -> int:
        """テスト用のsave_batch実装"""
        count = 0
        for data in data_list:
            try:
                if await self.save(data, **kwargs):
                    count += 1
            except RuntimeError:
                continue
        return count


class TestBaseSaver:
    """BaseSaverの単体テスト"""

    @pytest.mark.asyncio
    async def test_save_success(self):
        """正常な保存のテスト"""
        saver = ConcreteSaver()
        result = await saver.save({"id": 1, "value": "test"})
        assert result is True
        assert len(saver.saved_data) == 1
        assert saver.saved_data[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_save_error(self):
        """エラー時の動作テスト"""
        saver = ConcreteSaver()
        with pytest.raises(RuntimeError, match="Save failed"):
            await saver.save({"error": True})

    @pytest.mark.asyncio
    async def test_save_batch_success(self):
        """一括保存の正常動作テスト"""
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
        """一括保存時に一部エラーが発生する場合のテスト"""
        saver = ConcreteSaver()
        data_list = [
            {"id": 1, "value": "a"},
            {"error": True},
            {"id": 3, "value": "c"},
        ]
        count = await saver.save_batch(data_list)
        assert count == 2  # errorは除外される
        assert len(saver.saved_data) == 2

    @pytest.mark.asyncio
    async def test_validate_data(self):
        """データ検証のテスト"""
        saver = ConcreteSaver()

        assert await saver.validate_data({"id": 1}) is True
        assert await saver.validate_data(None) is False

    @pytest.mark.asyncio
    async def test_prepare_for_save(self):
        """保存前データ準備のテスト"""
        saver = ConcreteSaver()

        # 辞書型の場合
        data = {"id": 1, "value": "test"}
        result = await saver.prepare_for_save(data)
        assert result == {}  # 辞書にはmodel_dumpもdictもないため空辞書

    @pytest.mark.asyncio
    async def test_handle_save_error(self):
        """エラーハンドリングのテスト"""
        saver = ConcreteSaver()
        # デフォルトでは何もしない（例外を発生させない）
        await saver.handle_save_error({"id": 1}, RuntimeError("Test"))
