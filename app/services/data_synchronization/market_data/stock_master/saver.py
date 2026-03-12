"""Stock master saver utilities.

このモジュールは `StockMasterSaver` を提供し、マスターテーブル生成と
銘柄データの FK化を含むバッチ永続化処理を実装します。
"""

import logging
from typing import Any, Optional

from app.repositories.market_data.stock_master import (
    MarketCategoryMasterRepository,
    ScaleMasterRepository,
    Sector17MasterRepository,
    Sector33MasterRepository,
    StockMasterRepository,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StockMasterSaver:
    """銘柄マスタ + マスターテーブルレコードの永続化処理をカプセル化します.

    このクラスは以下のフローを実装：
    1. JPX raw データから unique なマスター値を抽出
    2. マスターテーブル（4個）を生成（upsert）
    3. raw stock data を FK参照に変換
    4. StockMaster を batch upsert
    """

    def __init__(self, stock_master_repo: StockMasterRepository, batch_size: int = 500):
        """初期化.

        Args:
            stock_master_repo: StockMaster 永続化用リポジトリ
            batch_size: batch 処理のサイズ
        """
        self.stock_master_repo = stock_master_repo
        self.session = stock_master_repo.session

        # マスター Repository を session.engine から初期化
        self.market_repo = MarketCategoryMasterRepository(self.session)
        self.sector_33_repo = Sector33MasterRepository(self.session)
        self.sector_17_repo = Sector17MasterRepository(self.session)
        self.scale_repo = ScaleMasterRepository(self.session)
        self.batch_size = batch_size

    async def _create_masters(self, data_dict: dict[str, Any]) -> dict[str, Any]:
        """マスターテーブル作成（upsert）.

        Args:
            data_dict (dict): fetcher.fetch_and_extract_masters() の戻り値

        Returns:
            dict[str, Any]: マスターオブジェクトのマッピング
        """
        logger.info("Creating master tables...")

        # Step 1: 市場区分マスター
        market_masters = {}
        for code, name in data_dict.get("market_categories", {}).items():
            market_master, _ = await self.market_repo.get_or_create(code, name)
            market_masters[code] = market_master

        # Step 2: 業種33マスター
        sector_33_masters = {}
        for code, name in data_dict.get("sector_33", {}).items():
            sector_33_master, _ = await self.sector_33_repo.get_or_create(code, name)
            sector_33_masters[code] = sector_33_master

        # Step 3: 業種17マスター
        sector_17_masters = {}
        for code, name in data_dict.get("sector_17", {}).items():
            sector_17_master, _ = await self.sector_17_repo.get_or_create(code, name)
            sector_17_masters[code] = sector_17_master

        # Step 4: 規模マスター
        scale_masters = {}
        for code, name in data_dict.get("scale", {}).items():
            scale_master, _ = await self.scale_repo.get_or_create(code, name)
            scale_masters[code] = scale_master

        logger.info(
            "✅ Masters created",
            extra={
                "market_count": len(market_masters),
                "sector_33_count": len(sector_33_masters),
                "sector_17_count": len(sector_17_masters),
                "scale_count": len(scale_masters),
            },
        )

        return {
            "market_masters": market_masters,
            "sector_33_masters": sector_33_masters,
            "sector_17_masters": sector_17_masters,
            "scale_masters": scale_masters,
        }

    async def _prepare_stock_data(
        self,
        stocks: list[dict[str, Any]],
        master_map: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """raw stock data を FK参照に変換.

        Args:
            stocks (list[dict]): JPX からの正規化済みデータ（dict形式）
            master_map (dict): _create_masters() の戻り値

        Returns:
            list[dict]: FK参照に変換されたレコード辞書リスト
        """
        logger.info(f"Preparing {len(stocks)} stock records...")

        prepared = []
        for stock in stocks:
            # stock が dict の場合と StockMasterNormalized オブジェクトの場合に対応
            market_category = (
                stock.get("market_category") if isinstance(stock, dict) else stock.market_category
            )
            sector_code_33 = (
                stock.get("sector_code_33") if isinstance(stock, dict) else stock.sector_code_33
            )
            sector_code_17 = (
                stock.get("sector_code_17") if isinstance(stock, dict) else stock.sector_code_17
            )
            scale_code = stock.get("scale_code") if isinstance(stock, dict) else stock.scale_code

            # マスターテーブルから ID 取得
            market_obj = master_map["market_masters"].get(market_category)
            sector_33_obj = master_map["sector_33_masters"].get(sector_code_33)
            sector_17_obj = master_map["sector_17_masters"].get(sector_code_17)
            scale_obj = master_map["scale_masters"].get(scale_code)

            # stock_code, stock_name, data_date, is_active をdict/objの両方に対応
            stock_code = stock.get("stock_code") if isinstance(stock, dict) else stock.stock_code
            stock_name = stock.get("stock_name") if isinstance(stock, dict) else stock.stock_name
            data_date = stock.get("data_date") if isinstance(stock, dict) else stock.data_date
            is_active = stock.get("is_active") if isinstance(stock, dict) else stock.is_active

            # FK 参照に変換
            prepared_record = {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "market_category_id": market_obj.id if market_obj else None,
                "sector_33_id": sector_33_obj.id if sector_33_obj else None,
                "sector_17_id": sector_17_obj.id if sector_17_obj else None,
                "scale_id": scale_obj.id if scale_obj else None,
                "data_date": data_date,
                "is_active": is_active,
            }
            prepared.append(prepared_record)

        return prepared

    async def save_with_masters(self, data_dict: dict[str, Any]) -> int:
        """End-to-end: マスター生成 + StockMaster FK化セーブ.

        Args:
            data_dict (dict): fetcher.fetch_and_extract_masters() の戻り値

        Returns:
            int: 処理した StockMaster レコード数

        Raises:
            Exception: 予期しないエラー発生時（トランザクション rollback 後に re-raise）
        """
        try:
            # Step 1: マスターテーブル作成
            masters = await self._create_masters(data_dict)

            # Step 2: stock data 変換
            prepared_stocks = await self._prepare_stock_data(data_dict["stocks"], masters)

            # Step 3: StockMaster UPSERT（batch 処理）
            total_records = await self._upsert_stock_master_batch(prepared_stocks)

            logger.info("✅ All data saved successfully", extra={"total_stocks": total_records})
            return total_records

        except Exception as e:
            await self.session.rollback()
            logger.error(f"❌ Error during save: {e}")
            raise

    async def _upsert_stock_master_batch(self, records: list[dict[str, Any]]) -> int:
        """StockMaster batch upsert.

        既存データを削除した上で、新規データを一括挿入します。

        Args:
            records (list[dict]): FK 参照に変換されたレコード辞書リスト

        Returns:
            int: upsert 処理した合計件数
        """
        # 既存データ削除
        await self.stock_master_repo.delete_all()

        if not records:
            return 0

        # batch upsert
        total = 0
        for i in range(0, len(records), self.batch_size):
            chunk = records[i : i + self.batch_size]
            affected = await self.stock_master_repo.bulk_upsert(chunk)
            total += int(affected or 0)
            logger.info(
                f"Processed batch",
                extra={"batch_number": i // self.batch_size + 1, "batch_size": len(chunk)},
            )

        return total


__all__ = ["StockMasterSaver"]
