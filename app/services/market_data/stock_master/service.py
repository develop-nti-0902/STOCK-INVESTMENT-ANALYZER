from datetime import datetime, timezone
from typing import List, Optional, Set

from app.repositories.stock_master_repository import StockMasterRepository
from app.repositories.stock_master_updates_repository import (
    StockMasterUpdatesRepository,
)
from app.services.market_data.stock_master.fetcher import StockMasterFetcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockMasterService:
    """Service layer for stock master operations.

    Responsibilities:
        - Retrieve data from fetcher
        - Convert Pydantic models to dicts for persistence
        - Call repository ``bulk_upsert`` in batches

    Attributes:
        repo (StockMasterRepository): 永続化リポジトリ
        fetcher (StockMasterFetcher): データ取得フェッチャー
    """

    def __init__(
        self,
        repo: StockMasterRepository,
        fetcher: Optional[StockMasterFetcher] = None,
        updates_repo: Optional[StockMasterUpdatesRepository] = None,
    ):
        """Initialize the service.

        Args:
            repo (StockMasterRepository): StockMaster データ用リポジトリ
            fetcher (Optional[StockMasterFetcher]): フェッチャー（未指定時はデフォルトを生成）

        """
        self.repo = repo
        self.fetcher = fetcher or StockMasterFetcher()
        # 更新サマリを記録するためのオプショナルなリポジトリ
        self.updates_repo = updates_repo

    async def fetch_and_store(
        self, *, batch_size: int = 500, limit: Optional[int] = None
    ) -> int:
        """Fetch stock master records and store them in DB in batches.

        Args:
            batch_size (int): バッチのサイズ（デフォルト: 500）
            limit (Optional[int]): フェッチ後に保存する上限件数（指定しない場合は全件）

        Returns:
            int: 保存されたレコードの合計数.

        Raises:
            Exception: フェッチや保存処理で発生した例外を透過します.
        """
        # フェッチ（リトライなし）
        try:
            data = await self.fetcher.fetch_all()
        except Exception as exc:
            logger.error("Failed to fetch data", extra={"error": str(exc)})
            raise

        # limitが指定されていれば先頭からsliceする
        if limit is not None:
            try:
                limit_val = int(limit)
                if limit_val < 0:
                    raise ValueError("limit must be >= 0")
            except (TypeError, ValueError) as exc:
                logger.error(
                    "Invalid limit value",
                    extra={"limit": limit, "error": str(exc)},
                )
                raise
            data = data[:limit_val]

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
            except Exception as exc:
                logger.error("bulk_upsert failed", extra={"error": str(exc)})
                raise

        logger.info(
            "fetch_and_store completed", extra={"total": total_processed}
        )
        return total_processed

    async def get_all_active_symbols(self) -> List[str]:
        """Return all active stock symbols.

        Returns:
            List[str]: アクティブな銘柄コードのリスト.

        Raises:
            Exception: リポジトリ呼び出しで発生した例外を透過します.
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
        """Get symbols filtered by market.

        Args:
            market (str): 市場名（例: "プライム", "スタンダード", "グロース"）

        Returns:
            List[str]: 指定市場のアクティブな銘柄コードのリスト.

        Raises:
            Exception: リポジトリ呼び出し中に発生した例外を透過します.
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
        """Get symbols filtered by sector.

        Args:
            sector (str): 業種名

        Returns:
            List[str]: 指定業種のアクティブな銘柄コードのリスト.

        Raises:
            Exception: リポジトリ呼び出し中に発生した例外を透過します.
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
        """Refresh stock master by fetching and storing latest data.

        Returns:
            int: 更新された件数.

        Raises:
            Exception: 内部で発生した例外を透過します.
        """
        record_id = None
        try:
            # 差分計算のために現在の既存シンボルを取得する
            existing_symbols: Set[str] = set()
            if self.updates_repo:
                try:
                    existing_symbols = set(
                        await self.repo.get_all_active_symbols()
                    )
                except Exception:
                    existing_symbols = set()

            # updates_repo がある場合、実行中のサマリレコードを作成する
            if self.updates_repo:
                rec = await self.updates_repo.create_summary(
                    {
                        "update_type": "refresh",
                        "total_stocks": 0,
                        "status": "running",
                        "added_stocks": 0,
                        "updated_stocks": 0,
                        "removed_stocks": 0,
                    }
                )
                record_id = getattr(rec, "id", None)

            # データを取得（既存挙動を保持するためリトライは行わない）
            data = await self.fetcher.fetch_all()

            # サマリ用にシンボル集合を計算する
            new_symbols = []
            for item in data:
                if not hasattr(item, "model_dump"):
                    raise TypeError(
                        "Expected Pydantic v2 model with model_dump(),"
                        f" got {type(item)!r}"
                    )
                dumped = item.model_dump(exclude_none=True)
                # dump した辞書に `stock_code` があると仮定する
                code = dumped.get("stock_code") or dumped.get("symbol")
                if code:
                    new_symbols.append(code)

            new_set = set(new_symbols)
            total = len(new_symbols)
            added = len(new_set - existing_symbols)
            updated = len(new_set & existing_symbols)
            removed = len(existing_symbols - new_set)

            # fetch_and_store と同様にバッチで upsert を行う
            total_processed = 0
            batch_size = 500
            for i in range(0, len(data), batch_size):
                batch = data[i : i + batch_size]
                prepared = [
                    item.model_dump(exclude_none=True) for item in batch
                ]
                affected = await self.repo.bulk_upsert(prepared)
                total_processed += int(affected or 0)

            # サマリを成功として更新する
            if self.updates_repo and record_id is not None:
                await self.updates_repo.update_status(
                    record_id,
                    "success",
                    {
                        "completed_at": datetime.now(timezone.utc),
                        "total_stocks": total,
                        "added_stocks": added,
                        "updated_stocks": updated,
                        "removed_stocks": removed,
                    },
                )

            logger.info(
                "Stock master refreshed",
                extra={"updated_count": total_processed},
            )
            return total_processed
        except Exception as exc:
            logger.error(
                "Failed to refresh stock master", extra={"error": str(exc)}
            )
            # 可能であれば更新テーブル上で失敗をマークする
            if self.updates_repo and record_id is not None:
                try:
                    await self.updates_repo.update_status(
                        record_id,
                        "failed",
                        {
                            "completed_at": datetime.now(timezone.utc),
                            "error_message": str(exc),
                        },
                    )
                except Exception:
                    logger.exception("Failed to mark summary as failed")
            raise

    async def reset_stock_master(self) -> int:
        """Delete all stock master records.

        Returns:
            int: 削除された件数.

        Raises:
            Exception: リポジトリ操作中に発生した例外を透過します.
        """
        try:
            # 銘柄マスタのレコードを削除する
            deleted_count = await self.repo.delete_all()

            # updates_repo があればサマリも削除する
            if self.updates_repo:
                try:
                    await self.updates_repo.delete_by_reset()
                except Exception:
                    logger.exception(
                        "Failed to delete stock_master_updates during reset"
                    )

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
