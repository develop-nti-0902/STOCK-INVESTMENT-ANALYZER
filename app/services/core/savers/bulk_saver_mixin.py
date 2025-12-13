"""
一括保存共通ロジック Mixin

大量データのバッチ保存時に使用する共通処理を提供します。
チャンク分割、進捗管理、エラーハンドリングを実装します。

仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

import asyncio
import logging
from typing import Any, Callable, Generic, TypeVar, cast

from app.services.core.savers.base_saver import BaseSaver

# ジェネリック型パラメータ: 保存するデータ型
T = TypeVar("T")

logger = logging.getLogger(__name__)


class BulkSaverMixin(BaseSaver[T], Generic[T]):
    """
    一括保存共通ロジック Mixin

    大量データの保存時にチャンク分割と進捗管理を提供します。
    BaseSaverを継承したクラスでこのMixinを使用することで、
    効率的なバッチ保存が可能になります。

    Attributes:
        batch_size (int): デフォルトのバッチサイズ
        max_concurrent_batches (int): 最大同時実行バッチ数

    Examples:
        >>> class StockPriceSaver(BulkSaverMixin[StockData]):
        ...     def __init__(self, batch_size: int = 1000):
        ...         super().__init__(batch_size=batch_size)
        ...
        ...     async def save(self, data: StockData) -> bool:
        ...         # 単一保存の実装
        ...         return True
        ...
        ...     async def save_batch(self, data_list: list[StockData]) -> int:
        ...         # 一括保存でチャンク処理を使用
        ...         return await self.save_in_chunks(data_list)
    """

    def __init__(
        self, batch_size: int = 1000, max_concurrent_batches: int = 3
    ):
        """
        BulkSaverMixinの初期化

        Args:
            batch_size: 1回のバッチ処理で保存するレコード数
            max_concurrent_batches: 最大同時実行バッチ数（並列処理制御）
        """
        self.batch_size = batch_size
        self.max_concurrent_batches = max_concurrent_batches

    async def save_in_chunks(
        self,
        data_list: list[T],
        chunk_size: int | None = None,
        progress_callback: Callable[..., Any] | None = None,
    ) -> int:
        """
        データをチャンクに分割して一括保存

        Args:
            data_list: 保存するデータのリスト
            chunk_size: チャンクサイズ（指定がない場合はself.batch_sizeを使用）
            progress_callback: 進捗通知用コールバック関数

        Returns:
            int: 保存に成功した総レコード数

        Raises:
            ValueError: データリストが不正な場合
            RuntimeError: 保存処理でエラーが発生した場合

        Note:
            各チャンクは並列で処理され、全体の進捗を追跡します。
        """
        if not data_list:
            logger.warning("No data to save")
            return 0

        actual_chunk_size = chunk_size or self.batch_size
        total_records = len(data_list)

        logger.info(
            "Starting chunked save: total_records=%s, chunk_size=%s",
            total_records,
            actual_chunk_size,
        )

        # データをチャンクに分割
        chunks = [
            data_list[i : i + actual_chunk_size]
            for i in range(0, total_records, actual_chunk_size)
        ]

        total_saved = 0
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def save_chunk_with_semaphore(
            chunk: list[T], chunk_index: int
        ) -> int:
            """セマフォ制御付きチャンク保存"""
            async with semaphore:
                try:
                    saved_count = await self._execute_bulk_insert(chunk)
                    logger.debug(
                        "Chunk %s/%s saved successfully: %s records",
                        chunk_index + 1,
                        len(chunks),
                        saved_count,
                    )

                    # 進捗コールバック
                    if progress_callback:
                        current_total = total_saved + saved_count
                        await progress_callback(
                            chunk_index + 1,
                            len(chunks),
                            saved_count,
                            current_total,
                        )

                    return saved_count

                except (
                    Exception
                ) as e:  # pylint: disable=broad-exception-caught
                    logger.error(
                        "Failed to save chunk %s: %s",
                        chunk_index + 1,
                        e,
                    )
                    # Continue processing other chunks even if one fails
                    return 0

        # 全チャンクを並列処理
        tasks = [
            save_chunk_with_semaphore(chunk, i)
            for i, chunk in enumerate(chunks)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Exception in chunk %s: %s", i + 1, result)
            else:
                total_saved += cast(int, result)

        logger.info(
            "Chunked save completed: total_saved=%s/%s",
            total_saved,
            total_records,
        )

        if total_saved < total_records:
            logger.warning(
                "Some data failed to save: success=%s, failed=%s",
                total_saved,
                total_records - total_saved,
            )

        return total_saved

    async def _execute_bulk_insert(self, chunk: list[T]) -> int:
        """
        チャンクごとの一括挿入処理（サブクラスで実装）

        Args:
            chunk: 保存するデータのチャンク

        Returns:
            int: 保存に成功したレコード数

        Raises:
            NotImplementedError: サブクラスで実装されていない場合
            RuntimeError: 保存処理でエラーが発生した場合

        Note:
            このメソッドはサブクラスでオーバーライドして、
            実際のDB保存処理を実装してください。
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} で _execute_bulk_insert が実装されていません"
        )

    async def validate_batch_data(self, data_list: list[T]) -> list[T]:
        """
        バッチデータの検証

        Args:
            data_list: 検証対象のデータリスト

        Returns:
            list[T]: 検証済みのデータリスト（無効データは除外）

        Note:
            デフォルトでは全てのデータを有効とみなします。
            サブクラスで独自の検証ロジックを実装可能です。
        """
        validated_data = []
        for data in data_list:
            if await self.validate_data(data):
                validated_data.append(data)
            else:
                logger.warning("Invalid data detected: %s", data)

        return validated_data

    def get_progress_info(self, current: int, total: int) -> dict[str, Any]:
        """
        進捗情報を取得

        Args:
            current: 現在の処理数
            total: 総処理数

        Returns:
            dict[str, Any]: 進捗情報
        """
        progress_percentage = (current / total * 100) if total > 0 else 0

        return {
            "current": current,
            "total": total,
            "percentage": round(progress_percentage, 2),
            "remaining": total - current,
        }
