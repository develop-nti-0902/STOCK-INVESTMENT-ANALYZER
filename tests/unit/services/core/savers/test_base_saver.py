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
        # Arrange: テスト用のSaverと保存データを準備
        saver = ConcreteSaver()
        data = {"id": 1, "value": "test"}

        # Act: データを保存
        result = await saver.save(data)

        # Assert: 保存が成功し内部状態が更新されていることを検証
        assert result is True
        assert len(saver.saved_data) == 1
        assert saver.saved_data[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_save_error(self):
        """エラー時の動作テスト"""
        # Arrange: テスト用のSaverを準備
        saver = ConcreteSaver()

        # Act / Assert: エラーが発生することを確認
        with pytest.raises(RuntimeError, match="Save failed"):
            await saver.save({"error": True})

    @pytest.mark.asyncio
    async def test_save_batch_success(self):
        """一括保存の正常動作テスト"""
        # Arrange: テスト用のSaverと保存対象リストを準備
        saver = ConcreteSaver()
        data_list = [
            {"id": 1, "value": "a"},
            {"id": 2, "value": "b"},
            {"id": 3, "value": "c"},
        ]

        # Act: 一括保存を実行
        count = await saver.save_batch(data_list)

        # Assert: すべて保存されたことを検証
        assert count == 3
        assert len(saver.saved_data) == 3

    @pytest.mark.asyncio
    async def test_save_batch_with_errors(self):
        """一括保存時に一部エラーが発生する場合のテスト"""
        # Arrange: テスト用のSaverと一部エラーを含むリストを準備
        saver = ConcreteSaver()
        data_list = [
            {"id": 1, "value": "a"},
            {"error": True},
            {"id": 3, "value": "c"},
        ]

        # Act: 一括保存を実行（エラーはスキップされる想定）
        count = await saver.save_batch(data_list)

        # Assert: エラー要素が除外されていることを検証
        assert count == 2  # errorは除外される
        assert len(saver.saved_data) == 2

    @pytest.mark.asyncio
    async def test_validate_data(self):
        """データ検証のテスト"""
        # Arrange: テスト用のSaverを準備
        saver = ConcreteSaver()

        # Act: 様々な入力でvalidate_dataを実行
        res_valid = await saver.validate_data({"id": 1})
        res_none = await saver.validate_data(None)

        # Assert: 期待結果を検証
        assert res_valid is True
        assert res_none is False

    @pytest.mark.asyncio
    async def test_prepare_for_save(self):
        """保存前データ準備のテスト"""
        # Arrange: テスト用のSaverと辞書型データを準備
        saver = ConcreteSaver()

        # 辞書型の場合
        data = {"id": 1, "value": "test"}

        # Act: 保存前処理を実行
        result = await saver.prepare_for_save(data)

        # Assert: 辞書にはmodel_dumpもdictもないため空辞書が返ることを検証
        assert result == {}

    @pytest.mark.asyncio
    async def test_handle_save_error(self):
        """エラーハンドリングのテスト"""
        # Arrange: テスト用のSaverを準備
        saver = ConcreteSaver()

        # Act / Assert: デフォルト実装では例外が再送出されないことを確認
        await saver.handle_save_error({"id": 1}, RuntimeError("Test"))
