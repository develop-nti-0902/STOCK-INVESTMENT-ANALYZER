"""
株価データSaver

StockPriceSaverクラスを実装し、タイムフレームに応じたRepository選択とデータ変換を提供します。
DataFrameからDB形式への変換と一括保存をサポートします。

仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, cast

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stock_data_repository import (
    StockData1dRepository,
    StockData1hRepository,
    StockData1moRepository,
    StockData1mRepository,
    StockData1wkRepository,
    StockData5mRepository,
    StockData15mRepository,
    StockData30mRepository,
)
from app.services.core.savers.bulk_saver_mixin import BulkSaverMixin

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
    TIMEFRAME_REPOSITORIES = {
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
        max_concurrent_batches: int = 3,
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
        self.repositories: Dict[str, Any] = {}

        # Repositoryインスタンスの初期化
        for timeframe, repo_class in self.TIMEFRAME_REPOSITORIES.items():
            self.repositories[timeframe] = repo_class(
                self.session
            )  # type: ignore

    async def save(self, data: Dict[str, Any], **kwargs: Any) -> bool:
        """
        単一データ保存（BaseSaverの実装）

        Args:
            data: 保存するデータ（symbol, timeframe, recordsを含むDict）
            **kwargs: 追加パラメータ

        Returns:
            bool: 保存成功の場合True
        """
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        records = data.get("records", [])

        if not symbol or not timeframe or not records:
            return False

        # recordsをDataFrameに変換
        df = pd.DataFrame(records)
        return await self.save_single_stock_data(
            symbol, timeframe, df, **kwargs
        )

    async def save_batch(
        self, data_list: List[Dict[str, Any]], **kwargs: Any
    ) -> int:
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

        result = await self.save_batch_stocks(grouped_data, **kwargs)
        return sum(result.values())

    async def save_single_stock_data(
        self,
        symbol: str,
        timeframe: str,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
        **kwargs: Any,
    ) -> bool:
        """
        株価データを保存

        DataFrameまたは辞書のリストを受け取り、指定されたタイムフレームのRepositoryに保存します。

        Args:
            symbol: 銘柄コード
            timeframe: タイムフレーム ('1m', '5m', '15m', '30m',
                       '1h', '1d', '1wk', '1mo')
            data: 保存するデータ（DataFrameまたは辞書のリスト）
            **kwargs: 追加パラメータ

        Returns:
            bool: 保存成功の場合True

        Raises:
            ValueError: 無効なタイムフレームまたはデータ形式の場合
        """
        try:
            # Repository選択
            repository = self._select_repository(timeframe)
            if not repository:
                raise ValueError(f"Unsupported timeframe: {timeframe}")

            # データ変換
            db_records = self._prepare_data_for_db(symbol, data)

            if not db_records:
                logger.warning(
                    f"No valid data to save for symbol {symbol}, "
                    f"timeframe {timeframe}"
                )
                return False

            # 一括保存
            saved_count: int = await repository.upsert_bulk(db_records)
            logger.info(
                f"Saved {saved_count} records for symbol {symbol}, "
                f"timeframe {timeframe}"
            )

            return saved_count > 0

        except Exception as e:
            logger.error(
                f"Failed to save stock data for {symbol} ({timeframe}): {e}"
            )
            raise

    async def save_batch_stocks(
        self,
        data_dict: Dict[
            str, Dict[str, Union[pd.DataFrame, List[Dict[str, Any]]]]
        ],
        **kwargs: Any,
    ) -> Dict[str, int]:
        """
        複数銘柄の株価データを並列保存

        Args:
            data_dict: {symbol: {timeframe: data}} の形式
            **kwargs: 追加パラメータ

        Returns:
            Dict[str, int]: {symbol: 保存件数} の形式

        Example:
            >>> data = {
            ...     "7203": {"1d": df1, "1h": df2},
            ...     "9984": {"1d": df3}
            ... }
            >>> result = await saver.save_multiple_stocks(data)
        """
        results = {}

        # 全タスクを収集
        tasks = []
        for symbol, timeframe_data in data_dict.items():
            for timeframe, data in timeframe_data.items():
                tasks.append(
                    self._save_single_stock_async(symbol, timeframe, data)
                )

        # 並列実行
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果集計
        idx = 0
        for symbol, timeframe_data in data_dict.items():
            for timeframe in timeframe_data.keys():
                result = task_results[idx]
                if isinstance(result, Exception):
                    logger.error(
                        f"Failed to save {symbol} ({timeframe}): {result}"
                    )
                    results[f"{symbol}_{timeframe}"] = 0
                elif isinstance(result, bool):
                    results[f"{symbol}_{timeframe}"] = 1 if result else 0
                else:
                    results[f"{symbol}_{timeframe}"] = cast(int, result)
                idx += 1

        return results

    async def _save_single_stock_async(
        self,
        symbol: str,
        timeframe: str,
        data: Union[pd.DataFrame, List[Dict[str, Any]]],
    ) -> int:
        """
        単一銘柄保存の非同期ヘルパー

        Args:
            symbol: 銘柄コード
            timeframe: タイムフレーム
            data: 保存データ

        Returns:
            int: 保存件数
        """
        try:
            repository = self._select_repository(timeframe)
            if not repository:
                raise ValueError(f"Unsupported timeframe: {timeframe}")

            db_records = self._prepare_data_for_db(symbol, data)
            saved_count = await repository.upsert_bulk(db_records)
            return saved_count

        except Exception as e:
            logger.error(
                f"Error in _save_single_stock_async for {symbol} "
                f"({timeframe}): {e}"
            )
            raise

    def _select_repository(self, timeframe: str) -> Optional[Any]:
        """
        タイムフレームに応じたRepositoryを選択

        Args:
            timeframe: タイムフレーム識別子

        Returns:
            Any: 対応するRepositoryインスタンス、存在しない場合はNone
        """
        return self.repositories.get(timeframe)

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
            elif isinstance(data, list) and all(
                isinstance(item, dict) for item in data
            ):
                return self._convert_dict_list_to_db_records(symbol, data)

            else:
                raise ValueError(f"Unsupported data type: {type(data)}")

        except Exception as e:
            logger.error(f"Failed to prepare data for DB: {e}")
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
            raise ValueError(f"Missing required columns: {missing_columns}")

        records = []
        for _, row in df.iterrows():
            try:
                # timestampの変換
                timestamp = pd.to_datetime(row["timestamp"])
                if timestamp.tz is None:
                    # タイムゾーンなしの場合、UTCとみなす
                    timestamp = timestamp.tz_localize("UTC")

                record = {
                    "symbol": symbol,
                    "timestamp": timestamp.to_pydatetime(),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                }
                records.append(record)

            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid row: {e}")
                continue

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
        for item in data_list:
            try:
                # timestampの変換
                timestamp = pd.to_datetime(item["timestamp"])
                if timestamp.tz is None:
                    timestamp = timestamp.tz_localize("UTC")

                record = {
                    "symbol": symbol,
                    "timestamp": timestamp.to_pydatetime(),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": int(item["volume"]),
                }
                records.append(record)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid item: {e}")
                continue

        return records
