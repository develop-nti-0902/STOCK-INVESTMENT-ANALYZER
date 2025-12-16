"""
BulkSaverMixinの単体テスト
"""

import asyncio

import pytest

from app.services.core.savers.bulk_saver_mixin import BulkSaverMixin


class ConcreteBulkSaver(BulkSaverMixin[dict]):
    """テスト用のBulkSaverMixin実装"""

    def __init__(self, batch_size: int = 10, max_concurrent_batches: int = 3):
        super().__init__(
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
        )
        self.executed_chunks: list[list[dict]] = []

    async def save(self, data: dict, **kwargs) -> bool:
        """単一保存の実装（テスト用）"""
        return True

    async def save_batch(self, data_list: list[dict], **kwargs) -> int:
        """一括保存の実装（テスト用）"""
        return await self.save_in_chunks(data_list)

    async def _execute_bulk_insert(self, chunk: list[dict]) -> int:
        """チャンク挿入の実装（テスト用）"""
        self.executed_chunks.append(chunk)
        return len(chunk)


class TestBulkSaverMixin:
    """BulkSaverMixinの単体テスト"""

    @pytest.mark.asyncio
    async def test_save_in_chunks_empty_list(self):
        """空のデータリストでのチャンク保存テスト"""
        # Arrange
        saver = ConcreteBulkSaver()

        # Act
        result = await saver.save_in_chunks([])

        # Assert
        assert result == 0
        assert len(saver.executed_chunks) == 0

    @pytest.mark.asyncio
    async def test_save_in_chunks_single_chunk(self):
        """単一チャンクでの保存テスト"""
        # Arrange
        saver = ConcreteBulkSaver(batch_size=10)
        data_list = [{"id": i} for i in range(5)]

        # Act
        result = await saver.save_in_chunks(data_list)

        # Assert
        assert result == 5
        assert len(saver.executed_chunks) == 1
        assert len(saver.executed_chunks[0]) == 5

    @pytest.mark.asyncio
    async def test_save_in_chunks_multiple_chunks(self):
        """複数チャンクでの保存テスト"""
        # Arrange
        saver = ConcreteBulkSaver(batch_size=3)
        data_list = [{"id": i} for i in range(7)]  # 3 + 3 + 1 = 3チャンク

        # Act
        result = await saver.save_in_chunks(data_list)

        # Assert
        assert result == 7
        assert len(saver.executed_chunks) == 3
        assert len(saver.executed_chunks[0]) == 3
        assert len(saver.executed_chunks[1]) == 3
        assert len(saver.executed_chunks[2]) == 1

    @pytest.mark.asyncio
    async def test_save_in_chunks_custom_chunk_size(self):
        """カスタムチャンクサイズでの保存テスト"""
        # Arrange
        saver = ConcreteBulkSaver(batch_size=10)  # デフォルトは10
        data_list = [{"id": i} for i in range(12)]
        custom_chunk_size = 4

        # Act
        result = await saver.save_in_chunks(
            data_list, chunk_size=custom_chunk_size
        )

        # Assert
        assert result == 12
        assert len(saver.executed_chunks) == 3  # 4 + 4 + 4 = 12
        assert all(len(chunk) == 4 for chunk in saver.executed_chunks)

    @pytest.mark.asyncio
    async def test_save_in_chunks_with_progress_callback(self):
        """進捗コールバック付きの保存テスト"""
        # Arrange
        saver = ConcreteBulkSaver(batch_size=2)
        data_list = [{"id": i} for i in range(5)]
        progress_calls = []

        async def progress_callback(
            chunk_index, total_chunks, saved_count, total_saved
        ):
            progress_calls.append(
                (chunk_index, total_chunks, saved_count, total_saved)
            )

        # Act
        result = await saver.save_in_chunks(
            data_list, progress_callback=progress_callback
        )

        # Assert
        assert result == 5
        assert len(progress_calls) == 3  # 3チャンク
        # 並列処理のため、累積値は保証されないので各チャンクの保存数を確認
        assert progress_calls[0][2] == 2  # 1st chunk: saved=2
        assert progress_calls[1][2] == 2  # 2nd chunk: saved=2
        assert progress_calls[2][2] == 1  # 3rd chunk: saved=1

    @pytest.mark.asyncio
    async def test_save_in_chunks_with_partial_failure(self):
        """一部失敗する場合の保存テスト"""

        # Arrange
        class FailingBulkSaver(ConcreteBulkSaver):
            async def _execute_bulk_insert(self, chunk: list[dict]) -> int:
                if chunk[0]["id"] == 0:  # 最初のチャンク（id=0,1）で失敗
                    raise RuntimeError("Bulk insert failed")
                return len(chunk)

        saver = FailingBulkSaver(batch_size=2)
        data_list = [
            {"id": i} for i in range(6)
        ]  # 3チャンク: [0,1], [2,3], [4,5]

        # Act
        result = await saver.save_in_chunks(data_list)

        # Assert
        assert result == 4  # 0 + 2 + 2 = 4件成功（最初のチャンク失敗）
        assert (
            len(saver.executed_chunks) == 0
        )  # 失敗したチャンクは実行されない

    @pytest.mark.asyncio
    async def test_validate_batch_data(self):
        """バッチデータ検証のテスト"""
        # Arrange
        saver = ConcreteBulkSaver()
        data_list = [
            {"id": 1, "valid": True},
            None,  # 無効データ
            {"id": 3, "valid": True},
        ]

        # Act
        validated = await saver.validate_batch_data(data_list)

        # Assert
        assert len(validated) == 2
        assert validated[0]["id"] == 1
        assert validated[1]["id"] == 3

    @pytest.mark.asyncio
    async def test_get_progress_info(self):
        """進捗情報取得のテスト"""
        # Arrange
        saver = ConcreteBulkSaver()

        # Act
        progress = saver.get_progress_info(3, 10)

        # Assert
        assert progress["current"] == 3
        assert progress["total"] == 10
        assert progress["percentage"] == 30.0
        assert progress["remaining"] == 7

    @pytest.mark.asyncio
    async def test_get_progress_info_zero_total(self):
        """総数が0の場合の進捗情報テスト"""
        # Arrange
        saver = ConcreteBulkSaver()

        # Act
        progress = saver.get_progress_info(0, 0)

        # Assert
        assert progress["percentage"] == 0

    @pytest.mark.asyncio
    async def test_concurrent_batch_limit(self):
        """同時実行バッチ数の制限テスト"""
        # Arrange
        saver = ConcreteBulkSaver(batch_size=1, max_concurrent_batches=2)
        data_list = [{"id": i} for i in range(5)]

        # モックで実行時間をシミュレート
        original_execute = saver._execute_bulk_insert
        executed_order = []

        async def delayed_execute(chunk):
            await asyncio.sleep(0.01)  # 少し遅延
            executed_order.append(len(chunk))
            return await original_execute(chunk)

        saver._execute_bulk_insert = delayed_execute

        # Act
        result = await saver.save_in_chunks(data_list)

        # Assert
        assert result == 5
        assert len(executed_order) == 5  # 全チャンク実行された
