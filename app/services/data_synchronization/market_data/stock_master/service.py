"""Stock master service module.

サービス層: フェッチ -> 変換 -> 保存 のオーケストレーションを提供します.
"""

from datetime import datetime, timezone
from typing import List, Optional, Set

from app.repositories.market_data.stock_master import (
    StockCodeMappingRepository,
    StockMasterRepository,
    StockMasterUpdatesRepository,
)
from app.services.data_synchronization.market_data.stock_master.converter import (
    StockMasterConverter,
)
from app.services.data_synchronization.market_data.stock_master.fetcher import StockMasterFetcher
from app.services.data_synchronization.market_data.stock_master.saver import StockMasterSaver
from app.services.data_synchronization.market_data.stock_master.stock_code_mapping_saver import (
    StockCodeMappingSaver,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockMasterService:
    """銘柄マスター操作のためのサービス層.

    役割:
        - フェッチャーからデータを取得する
        - Pydanticモデルを永続化用の辞書に変換する
        - リポジトリの ``bulk_upsert`` をバッチ処理で呼び出す
        - 同時に stock_code_mapping も更新する

    属性:
        repo (StockMasterRepository): 永続化用リポジトリ
        fetcher (StockMasterFetcher): データ取得フェッチャー
        stock_code_mapping_repo (StockCodeMappingRepository): コード対応リポジトリ
    """

    def __init__(
        self,
        repo: StockMasterRepository,
        fetcher: Optional[StockMasterFetcher] = None,
        converter: Optional[StockMasterConverter] = None,
        saver: Optional[StockMasterSaver] = None,
        updates_repo: Optional[StockMasterUpdatesRepository] = None,
        stock_code_mapping_repo: Optional[StockCodeMappingRepository] = None,
        stock_code_mapping_saver: Optional[StockCodeMappingSaver] = None,
    ):
        """サービスを初期化します.

        Args:
            repo (StockMasterRepository): 銘柄マスタ用リポジトリ
            fetcher (Optional[StockMasterFetcher]): フェッチャー（未指定時はデフォルトを生成）
            stock_code_mapping_repo (Optional[StockCodeMappingRepository]): コード対応リポジトリ
            stock_code_mapping_saver (Optional[StockCodeMappingSaver]): コード対応Saver
        """
        self.repo = repo
        # デフォルト実装を割り当てることで呼び出し側が None を渡しても安全に動作する
        self.fetcher: StockMasterFetcher = fetcher or StockMasterFetcher()
        self.converter: StockMasterConverter = converter or StockMasterConverter()
        # Saver は repo を必要とするため、未指定の場合は repo を用いて生成する
        self.saver: StockMasterSaver = saver or StockMasterSaver(repo)
        self.updates_repo = updates_repo
        # stock_code_mapping 対応
        self.stock_code_mapping_repo = stock_code_mapping_repo
        self.stock_code_mapping_saver = stock_code_mapping_saver

    async def get_all_active_symbols(self) -> List[str]:
        """全てのアクティブな銘柄コードを返します.

        Returns:
            List[str]: アクティブな銘柄コードのリスト

        Raises:
            Exception: リポジトリ呼び出し中に発生した例外を透過します
        """
        try:
            symbols = await self.repo.get_all_active_symbols()
            logger.info("Retrieved all active symbols", extra={"count": len(symbols)})
            return symbols
        except Exception as exc:
            logger.error("Failed to get all active symbols", extra={"error": str(exc)})
            raise

    async def get_symbols_by_market(self, market: str) -> List[str]:
        """市場でフィルタした銘柄コードを返します.

        Args:
            market (str): 市場名（例: "プライム", "スタンダード", "グロース"）

        Returns:
            List[str]: 指定市場のアクティブな銘柄コードのリスト

        Raises:
            Exception: リポジトリ呼び出し中に発生した例外を透過します
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
        """業種でフィルタした銘柄コードを返します.

        Args:
            sector (str): 業種名

        Returns:
            List[str]: 指定業種のアクティブな銘柄コードのリスト

        Raises:
            Exception: リポジトリ呼び出し中に発生した例外を透過します
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

    async def fetch_and_save(self, limit: Optional[int] = None, batch_size: int = 500) -> int:
        """銘柄マスターをフェッチして保存します.

        Args:
            limit (Optional[int]): フェッチ後に保存する上限件数（未指定で全件）
            batch_size (int): バッチサイズ（デフォルト: 500）

        Returns:
            int: 永続化に成功したレコード数

        Raises:
            Exception: 内部で発生した例外を透過します
        """
        record_id = None
        try:
            # 差分計算のために現在の既存シンボルを取得する
            existing_symbols: Set[str] = set()
            if self.updates_repo:
                try:
                    existing_symbols = set(await self.repo.get_all_active_symbols())
                except Exception:
                    existing_symbols = set()

            # updates_repo がある場合、実行中のサマリレコードを作成する
            if self.updates_repo:
                summary = await self.updates_repo.create_summary(
                    {
                        "update_type": "fetch",
                        "total_stocks": 0,
                        "status": "running",
                        "added_stocks": 0,
                        "updated_stocks": 0,
                        "removed_stocks": 0,
                    }
                )
                record_id = getattr(summary, "id", None)
            ##########################################################
            # フェッチ: データ取得 + マスターテーブル値抽出
            ##########################################################
            data_dict = await self.fetcher.fetch_and_extract_masters()
            stocks_data = data_dict.get("stocks", [])

            # StockMasterNormalized オブジェクトを dict に変換
            stocks_data_dicts = [item.model_dump() for item in stocks_data]

            # limit が指定されていればフィルタ
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
                stocks_data_dicts = stocks_data_dicts[:limit_val]
                data_dict["stocks"] = stocks_data_dicts

            # サマリ用にシンボル集合を計算する
            new_symbols = []
            for item in stocks_data_dicts:
                stock_code = item.get("stock_code") or item.get("symbol")
                if stock_code:
                    new_symbols.append(stock_code)

            new_set = set(new_symbols)
            total = len(new_symbols)
            added = len(new_set - existing_symbols)
            updated = len(new_set & existing_symbols)
            removed = len(existing_symbols - new_set)

            ##########################################################
            # 保存: Saver に委譲（マスターテーブル作成 + FK変換 + 永続化）
            ##########################################################
            total_processed = await self.saver.save_with_masters(data_dict)

            ##########################################################
            # stock_code_mapping を同時に保存
            ##########################################################
            if self.stock_code_mapping_repo and self.stock_code_mapping_saver:
                try:
                    mapping_records = self._generate_stock_code_mappings(stocks_data_dicts)
                    if mapping_records:
                        await self.stock_code_mapping_saver.save_batch(
                            mapping_records, batch_size=batch_size
                        )
                        logger.info(
                            "Stock code mappings saved",
                            extra={"count": len(mapping_records)},
                        )
                except Exception as exc:
                    logger.warning(
                        "Failed to save stock code mappings",
                        extra={"error": str(exc)},
                    )
                    # マッピング保存エラーは致命的ではないため、続行する

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
                "Stock master fetched",
                extra={"updated_count": total_processed},
            )
            return total_processed
        except Exception as exc:
            logger.error("Failed to fetch stock master", extra={"error": str(exc)})
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

    def _generate_stock_code_mappings(self, records: List[dict]) -> List[dict]:
        """stock_master のレコードから stock_code_mapping レコードを生成します.

        JPX 株式コード（stock_code）から EDINET 提出企業コード（sec_code）を
        自動生成し、対応レコードを作成します。

        Args:
            records (List[dict]): stock_master のレコード辞書リスト

        Returns:
            List[dict]: stock_code_mapping の レコード辞書リスト
        """
        mappings: List[dict] = []
        for record in records:
            stock_code = record.get("stock_code")
            if not stock_code:
                continue

            # sec_code = stock_code + "0" で生成
            # 例：「1301」 -> 「13010」
            sec_code = f"{stock_code}0"

            mappings.append(
                {
                    "stock_code": stock_code,
                    "sec_code": sec_code,
                }
            )

        return mappings

    async def reset_stock_master(self) -> int:
        """銘柄マスターの全レコードを削除します.

        Returns:
            int: 削除された件数

        Raises:
            Exception: リポジトリ操作中に発生した例外を透過します
        """
        try:
            # 銘柄マスタのレコードを削除する
            deleted_count = await self.repo.delete_all()

            # updates_repo があればサマリも削除する
            if self.updates_repo:
                try:
                    await self.updates_repo.delete_by_reset()
                except Exception:
                    logger.exception("Failed to delete stock_master_updates during reset")

            logger.info(
                "Stock master reset completed",
                extra={"deleted_count": deleted_count},
            )
            return deleted_count
        except Exception as exc:
            logger.error("Failed to reset stock master", extra={"error": str(exc)})
            raise
