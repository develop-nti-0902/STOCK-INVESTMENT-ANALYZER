from typing import Optional

from app.repositories.stock_master_repository import StockMasterRepository
from app.services.market_data.stock_master.fetcher import StockMasterFetcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockMasterService:
    """
    銘柄マスタ向けのサービスレイヤ

    - フェッチャーからのデータ取得
    - 正規化済Pydanticモデルの辞書化
    - Repositoryのbulk_upsert呼び出し（バッチ処理）
    """

    def __init__(
        self,
        repo: StockMasterRepository,
        fetcher: Optional[StockMasterFetcher] = None,
    ):
        self.repo = repo
        self.fetcher = fetcher or StockMasterFetcher()

    async def fetch_and_store(
        self, source: str = "jpx", *, batch_size: int = 500
    ) -> int:
        """
        指定ソースから銘柄マスタを取得し、DBに保存する

        Returns:
            int: 登録（処理）した件数
        """
        if source != "jpx":
            raise ValueError(f"Unsupported source: {source}")

        # フェッチ（リトライなし）
        try:
            data = await self.fetcher.fetch_all()
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to fetch data", extra={"error": str(exc)})
            raise

        # バッチ処理でRepositoryに渡す
        total_processed = 0
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            # Pydanticモデルを辞書化
            prepared = []
            for item in batch:
                if not hasattr(item, "model_dump"):
                    raise TypeError(
                        "Expected Pydantic v2 model with model_dump(),"
                        f" got {type(item)!r}"
                    )
                prepared.append(item.model_dump(exclude_none=True))

            # リポジトリ側の処理（単純実行）
            try:
                affected = await self.repo.bulk_upsert(prepared)
                total_processed += int(affected or 0)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("bulk_upsert failed", extra={"error": str(exc)})
                raise

        logger.info(
            "fetch_and_store completed", extra={"total": total_processed}
        )
        return total_processed


__all__ = ["StockMasterService"]
