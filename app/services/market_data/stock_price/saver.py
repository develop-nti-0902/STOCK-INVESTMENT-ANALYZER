"""
株価データSaver

StockPriceSaverクラスを実装し、タイムフレームに応じたRepository選択とデータ変換を提供します。
DataFrameからDB形式への変換と一括保存をサポートします。

仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.validation import FieldValidationError
from app.repositories.stock_data_repository import (
    StockData1dRepository,
    StockData1hRepository,
    StockData1moRepository,
    StockData1mRepository,
    StockData1wkRepository,
    StockData5mRepository,
    StockData15mRepository,
    StockData30mRepository,
    StockDataRepository,
)
from app.services.core.savers.bulk_saver_mixin import BulkSaverMixin

# セッションは外部から注入される想定（FastAPIの依存注入 `get_db`）

logger = logging.getLogger(__name__)


class StockPriceSaver(BulkSaverMixin[Dict[str, Any]]):
    """
    株価データSaver

    タイムフレームに応じたRepositoryを選択し、DataFrameからDB形式への変換を行います。
    一括保存と単一保存の両方をサポートします。

    Attributes:
        session (AsyncSession): 非同期DBセッション
        repositories (Dict[str, Any]): タイムフレーム別Repositoryマップ
    """

    # タイムフレームとRepositoryクラスのマッピング
    TIMEFRAME_REPOSITORIES: Dict[str, Callable[[AsyncSession], StockDataRepository]] = {
        "1m": StockData1mRepository,
        "5m": StockData5mRepository,
        "15m": StockData15mRepository,
        "30m": StockData30mRepository,
        "1h": StockData1hRepository,
        "1d": StockData1dRepository,
        "1wk": StockData1wkRepository,
        "1mo": StockData1moRepository,
    }

    # DataFrameの必須カラム
    REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]

    def __init__(
        self,
        session: AsyncSession,
        batch_size: int = 1000,
        max_concurrent_batches: int = 25,
    ):
        """
        初期化

        Args:
            session: 非同期DBセッション
            batch_size: バッチサイズ
            max_concurrent_batches: 最大同時実行バッチ数
        """
        super().__init__(
            batch_size=batch_size,
            max_concurrent_batches=max_concurrent_batches,
        )
        self.session = session
        self.repositories: Dict[str, StockDataRepository] = {}

        # Repositoryインスタンスの初期化
        for timeframe, repo_class in self.TIMEFRAME_REPOSITORIES.items():
            self.repositories[timeframe] = repo_class(self.session)

    async def save_batch(self, data_list: List[Dict[str, Any]], **kwargs: Any) -> int:
        """
        一括データ保存（BaseSaverの実装）

        Args:
            data_list: 保存するデータのリスト
            **kwargs: 追加パラメータ

        Returns:
            int: 保存成功したレコード数
        """
        # data_listをsave_multiple_stocksの形式に変換
        grouped_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for data in data_list:
            symbol = data.get("symbol")
            timeframe = data.get("timeframe")
            records = data.get("records", [])

            if not symbol or not timeframe or not records:
                continue

            if symbol not in grouped_data:
                grouped_data[symbol] = {}
            if timeframe not in grouped_data[symbol]:
                grouped_data[symbol][timeframe] = []
            grouped_data[symbol][timeframe].extend(records)

        # grouped_data の処理をここに統合
        results: Dict[str, int] = {}

        symbols_items = list(grouped_data.items())
        if not symbols_items:
            return 0

        batch_size = max(1, getattr(self, "max_concurrent_batches", 20))

        for i in range(0, len(symbols_items), batch_size):
            batch = symbols_items[i : i + batch_size]
            for symbol, timeframe_data in batch:
                try:
                    per_symbol: Dict[str, int] = await self._save_symbol(symbol, timeframe_data)
                except Exception as e:
                    logger.error("Failed to save symbol %s: %s", symbol, e)
                    for tf in timeframe_data.keys():
                        results[f"{symbol}_{tf}"] = 0
                    # propagate exception to caller so caller can handle transaction
                    raise

                for tf in timeframe_data.keys():
                    results[f"{symbol}_{tf}"] = per_symbol.get(tf, 0)

        return sum(results.values())

    async def _save_symbol(
        self,
        symbol: str,
        timeframe_data: Dict[str, Union[pd.DataFrame, List[Dict[str, Any]]]],
    ) -> Dict[str, int]:
        """
        銘柄単位で複数タイムフレームをまとめて保存し、
        最後に一度だけコミット/ロールバックする。

        Returns:
            Dict[str,int]: {timeframe: saved_count} の辞書
        """
        # 注入されたセッション (`self.session`) のみを使用して保存処理を行う。
        # 内部でセッションを新たに作成することはありません。
        results: Dict[str, int] = {}
        try:
            for timeframe, data in timeframe_data.items():
                repository = self.repositories.get(timeframe)
                if not repository:
                    logger.error(
                        "Unsupported timeframe for symbol %s: %s",
                        symbol,
                        timeframe,
                    )
                    results[timeframe] = 0
                    continue

                db_records = self._prepare_data_for_db(symbol, data)
                if not db_records:
                    logger.warning(
                        "No DB records prepared for %s (%s)",
                        symbol,
                        timeframe,
                    )
                    results[timeframe] = 0
                    continue

                saved_count = await repository.upsert_bulk(db_records)
                results[timeframe] = saved_count

            # saver はコミットを行わない。トランザクションは呼び出し元で管理する。
            return results

        except Exception:
            logger.exception("Exception saving symbol (bulk) for %s", symbol)
            # 例外は呼び出し元へ伝搬させ、トランザクション管理は呼び出し元で行う
            raise

    def _prepare_data_for_db(
        self,
        symbol: str,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        DataFrameまたは辞書のリストをDB保存形式に変換

        Args:
            symbol: 銘柄コード
            data: 変換するデータ

        Returns:
            List[Dict[str, Any]]: DB保存形式のレコードリスト

        Raises:
            ValueError: データ形式が無効な場合
        """
        try:
            # DataFrameの場合
            if isinstance(data, pd.DataFrame):
                return self._convert_dataframe_to_db_records(symbol, data)

            # 辞書のリストの場合
            elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return self._convert_dict_list_to_db_records(symbol, data)

            else:
                raise FieldValidationError(message=f"Unsupported data type: {type(data)}")

        except Exception as e:
            logger.error("Failed to prepare data for DB: %s", e)
            raise

    def _convert_dataframe_to_db_records(
        self, symbol: str, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        DataFrameをDBレコード形式に変換

        Args:
            symbol: 銘柄コード
            df: 変換するDataFrame

        Returns:
            List[Dict[str, Any]]: DBレコードリスト
        """
        # 必須カラムの検証
        missing_columns = set(self.REQUIRED_COLUMNS) - set(df.columns)
        if missing_columns:
            raise FieldValidationError(message=f"Missing required columns: {missing_columns}")

        records = []
        skipped = 0
        for _, row in df.iterrows():
            try:
                # timestampの変換
                timestamp = pd.to_datetime(row["timestamp"])
                if timestamp.tz is None:
                    # タイムゾーンなしの場合、JST(Asia/Tokyo)とみなす
                    timestamp = timestamp.tz_localize("Asia/Tokyo")

                # 必須数値フィールドの欠損チェック
                if (
                    pd.isna(row.get("open"))
                    or pd.isna(row.get("high"))
                    or pd.isna(row.get("low"))
                    or pd.isna(row.get("close"))
                    or pd.isna(row.get("volume"))
                ):
                    skipped += 1
                    continue

                record = {
                    "symbol": symbol,
                    # 保存時は timezone-aware な timestamp をそのまま保持
                    "timestamp": timestamp.to_pydatetime(),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
                # 調整後終値があれば追加
                if "adj_close" in row and not pd.isna(row["adj_close"]):
                    try:
                        record["adj_close"] = float(row["adj_close"])
                    except Exception as e:
                        logger.warning(
                            "Failed to convert adj_close for symbol '%s': %s",
                            symbol,
                            e,
                        )
                # 値の論理整合性チェック (高値/安値/始値/終値の関係)
                eps = 1e-8
                open_val = record["open"]
                high_val = record["high"]
                low_val = record["low"]
                close_val = record["close"]
                if not (
                    high_val + eps >= low_val
                    and high_val + eps >= open_val
                    and high_val + eps >= close_val
                    and low_val - eps <= open_val
                    and low_val - eps <= close_val
                ):
                    logger.warning(
                        "Skipping row due to price logic violation: %s",
                        record,
                    )
                    continue

                records.append(record)

            except (ValueError, TypeError) as e:
                logger.warning("Skipping invalid row: %s", e)
                continue

        if skipped:
            logger.warning(
                "Skipped %d invalid rows for %s due to missing numeric fields",
                skipped,
                symbol,
            )

        return records

    def _convert_dict_list_to_db_records(
        self, symbol: str, data_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        辞書のリストをDBレコード形式に変換

        Args:
            symbol: 銘柄コード
            data_list: 変換する辞書のリスト

        Returns:
            List[Dict[str, Any]]: DBレコードリスト
        """
        records = []
        skipped = 0
        for item in data_list:
            try:
                # timestampの変換
                timestamp = pd.to_datetime(item["timestamp"])
                if timestamp.tz is None:
                    timestamp = timestamp.tz_localize("Asia/Tokyo")

                # 必須数値フィールドの欠損チェック
                if (
                    item.get("open") is None
                    or item.get("high") is None
                    or item.get("low") is None
                    or item.get("close") is None
                    or item.get("volume") is None
                    or pd.isna(item.get("open"))
                    or pd.isna(item.get("high"))
                    or pd.isna(item.get("low"))
                    or pd.isna(item.get("close"))
                    or pd.isna(item.get("volume"))
                ):
                    skipped += 1
                    continue

                record = {
                    "symbol": symbol,
                    "timestamp": timestamp.to_pydatetime(),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": int(item["volume"]),
                }
                # 辞書から adj_close が来ていれば追加
                if "adj_close" in item and item["adj_close"] is not None:
                    try:
                        record["adj_close"] = float(item["adj_close"])
                    except Exception as e:
                        logger.warning(
                            "Failed to convert adj_close for symbol '%s': %s",
                            symbol,
                            e,
                        )
                # 値の論理整合性チェック
                eps = 1e-8
                open_val = record["open"]
                high_val = record["high"]
                low_val = record["low"]
                close_val = record["close"]
                if not (
                    high_val + eps >= low_val
                    and high_val + eps >= open_val
                    and high_val + eps >= close_val
                    and low_val - eps <= open_val
                    and low_val - eps <= close_val
                ):
                    logger.warning(
                        "Skipping item due to price logic violation: %s",
                        record,
                    )
                    continue

                records.append(record)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning("Skipping invalid item: %s", e)
                continue

        if skipped:
            logger.warning(
                "Skipped %d invalid items for %s: missing numeric fields",
                skipped,
                symbol,
            )

        return records

    def _select_repository(self, timeframe: str) -> Optional[StockDataRepository]:
        """
        タイムフレームに応じたRepositoryを選択

        Args:
            timeframe: タイムフレーム識別子

        Returns:
            Any: 対応するRepositoryインスタンス、存在しない場合はNone
        """
        return self.repositories.get(timeframe)

    async def save(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        単一データ保存（BaseSaverの実装）

        Args:
            data: 保存するデータ（symbol, timeframe, recordsを含むDict）
            **kwargs: 追加パラメータ

        Notes:
            実処理では `save_batch` を使用しているため、
            単体の `save` は派生クラスで必要に応じて実装してください。
        """
        raise NotImplementedError("save is not implemented for saver. Implement when needed.")
