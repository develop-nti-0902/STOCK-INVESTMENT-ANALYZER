"""
株価データSaver

StockPriceSaverクラスを実装し、タイムフレームに応じたRepository選択とデータ変換を提供します。
DataFrameからDB形式への変換と一括保存をサポートします。

仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union, cast

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
    StockDataRepository,
)
from app.services.core.savers.bulk_saver_mixin import BulkSaverMixin
from app.utils.database import get_session_maker

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
    TIMEFRAME_REPOSITORIES: Dict[str, Type[StockDataRepository]] = {
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

        注意:
            このメソッドはFastAPIから注入されたセッション（self.session）を使用します。
            トランザクションのコミットは、FastAPIのget_db()が自動的に行います。
            エラーが発生した場合は、例外を上位層に伝播させてください（get_db()が自動ロールバック）。
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
        # 新しいセッションをシンボル単位で作成し、同一セッションの並列使用を避ける
        repo_class = self.TIMEFRAME_REPOSITORIES.get(timeframe)
        if not repo_class:
            logger.error(
                "Unsupported timeframe for symbol %s: %s", symbol, timeframe
            )
            return 0

        db_records = self._prepare_data_for_db(symbol, data)
        if not db_records:
            logger.warning(
                "No DB records prepared for %s (%s)", symbol, timeframe
            )
            return 0

        session_maker = get_session_maker()
        async with session_maker() as session:
            repository = repo_class(session)
            try:
                saved_count = await repository.upsert_bulk(db_records)
                # Repository層ではコミットしないため、Service層でコミット
                if saved_count > 0:
                    await session.commit()
                    logger.info(
                        "_save_single_stock_async: %s (%s) saved_count=%s "
                        "(committed)",
                        symbol,
                        timeframe,
                        saved_count,
                    )
                else:
                    # 成功件数が0の場合でもトランザクションを明示的にロールバックしてクリーンにする
                    await session.rollback()
                    logger.info(
                        "_save_single_stock_async: %s (%s) saved_count=0 "
                        "(rolled back)",
                        symbol,
                        timeframe,
                    )

                # 診断: saved_count が 0 の場合、代表レコードで upsert_single を試して例外内容を取得
                if saved_count == 0 and db_records:
                    try:
                        # upsert_single は例外を投げる設計なので、ここで捕まえてログを出す
                        await repository.upsert_single(db_records[0])
                    except Exception as ex_single:
                        logger.exception(
                            "Detailed upsert_single error for %s (%s): %s",
                            symbol,
                            timeframe,
                            ex_single,
                        )
                return saved_count

            except Exception as e:
                # 詳細な診断ログを出し、例外を外に投げず 0 を返す
                logger.exception(
                    "Exception saving symbol %s (%s): %s", symbol, timeframe, e
                )
                try:
                    await session.rollback()
                except Exception:
                    pass
                return 0

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
                    # タイムゾーンなしの場合、JST(Asia/Tokyo)とみなす
                    timestamp = timestamp.tz_localize("Asia/Tokyo")

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
                    timestamp = timestamp.tz_localize("Asia/Tokyo")

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
                logger.warning(f"Skipping invalid item: {e}")
                continue

        return records
