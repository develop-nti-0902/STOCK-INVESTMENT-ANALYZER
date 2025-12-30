from typing import List, Optional

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

    async def fetch_and_store(self, *, batch_size: int = 500) -> int:
        """
        JPXから銘柄マスタを取得し、DBに保存する

        Returns:
            int: 登録（処理）した件数
        """
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

    async def get_all_active_symbols(self) -> List[str]:
        """
        アクティブな全銘柄コードを取得

        Returns:
            List[str]: アクティブな銘柄コードのリスト
        """
        try:
            symbols = await self.repo.get_all_active_symbols()
            logger.info(
                "Retrieved all active symbols", extra={"count": len(symbols)}
            )
            return symbols
        except Exception as exc:
            logger.error(
                "Failed to get all active symbols", extra={"error": str(exc)}
            )
            raise

    async def get_symbols_by_market(self, market: str) -> List[str]:
        """
        市場別銘柄コードを取得

        Args:
            market: 市場名（例: "プライム", "スタンダード", "グロース"）

        Returns:
            List[str]: 指定市場のアクティブな銘柄コードのリスト
        """
        try:
            symbols = await self.repo.get_symbols_by_market(market)
            logger.info(
                "Retrieved symbols by market",
                extra={"market": market, "count": len(symbols)},
            )
            return symbols
        except Exception as exc:
            logger.error(
                "Failed to get symbols by market",
                extra={"market": market, "error": str(exc)},
            )
            raise

    async def get_symbols_by_sector(self, sector: str) -> List[str]:
        """
        業種別銘柄コードを取得

        Args:
            sector: 業種名

        Returns:
            List[str]: 指定業種のアクティブな銘柄コードのリスト
        """
        try:
            symbols = await self.repo.get_symbols_by_sector(sector)
            logger.info(
                "Retrieved symbols by sector",
                extra={"sector": sector, "count": len(symbols)},
            )
            return symbols
        except Exception as exc:
            logger.error(
                "Failed to get symbols by sector",
                extra={"sector": sector, "error": str(exc)},
            )
            raise

    async def refresh_stock_master(self) -> int:
        """
        銘柄マスタを最新情報で更新

        Returns:
            int: 更新された件数
        """
        try:
            updated_count = await self.fetch_and_store()
            logger.info(
                "Stock master refreshed",
                extra={"updated_count": updated_count},
            )
            return updated_count
        except Exception as exc:
            logger.error(
                "Failed to refresh stock master", extra={"error": str(exc)}
            )
            raise

    async def reset_stock_master(self) -> int:
        """
        銘柄マスタの全データを削除

        Returns:
            int: 削除された件数
        """
        try:
            deleted_count = await self.repo.delete_all()
            logger.info(
                "Stock master reset completed",
                extra={"deleted_count": deleted_count},
            )
            return deleted_count
        except Exception as exc:
            logger.error(
                "Failed to reset stock master", extra={"error": str(exc)}
            )
            raise
