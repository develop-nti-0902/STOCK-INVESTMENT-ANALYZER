"""Stock master saver utilities.

このモジュールは `StockMasterSaver` を提供し、バッチでの永続化処理を簡易化します.
"""

from typing import List, Optional

from app.repositories.stock_master_repository import StockMasterRepository


class StockMasterSaver:
    """銘柄マスタレコードの永続化処理をカプセル化します.

    このラッパーはリポジトリの`bulk_upsert`をバッチで呼び出します。
    トランザクション境界（コミット／ロールバック）は管理しないため、
    必要に応じて呼び出し側（サービス層）で制御できます。
    """

    def __init__(self, repo: StockMasterRepository, batch_size: int = 500):
        """初期化.

        Args:
            repo: 永続化用リポジトリ
            batch_size: チャンク処理のサイズ
        """
        self.repo = repo
        self.batch_size = batch_size

    async def save_batch(self, records: List[dict], batch_size: Optional[int] = None) -> int:
        """レコードをチャンクに分けてリポジトリの`bulk_upsert`で永続化します.

        Args:
            records: コンバータで準備したレコード辞書のリスト
            batch_size: チャンクサイズの上書き（省略時はデフォルトを使用）

        Returns:
            int: 処理した合計レコード数（チャンクごとの合計）
        """
        if not records:
            return 0

        size = batch_size or self.batch_size
        total = 0
        for i in range(0, len(records), size):
            chunk = records[i : i + size]
            affected = await self.repo.bulk_upsert(chunk)
            total += int(affected or 0)

        return total


__all__ = ["StockMasterSaver"]
