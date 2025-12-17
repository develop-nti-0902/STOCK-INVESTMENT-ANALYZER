"""
株価データ変換層

yfinance DataFrameをPydanticモデルに変換し、さらにDB保存用の辞書形式に変換する機能を提供します。
仕様書: docs/architecture/layers/service_layer.md 3.2.2章
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import ValidationError

from app.schemas.stock_data import StockPriceCreate
from app.services.core.converters.base_converter import BaseConverter

logger = logging.getLogger(__name__)


class StockPriceConverter(BaseConverter[StockPriceCreate]):
    """
    株価データ変換クラス

    yfinanceから取得したDataFrameをPydanticモデルに変換し、
    DB保存用の辞書形式に変換する機能を提供します。

    BaseConverter[StockPriceCreate]を継承し、標準的な変換インターフェースを実装します。
    """

    def __init__(self):
        """初期化"""
        super().__init__()

    def to_pydantic(self, data: Any) -> StockPriceCreate:
        """
        単一データ → StockPriceCreate変換

        Note: このクラスでは主にDataFrameからの変換を使用するため、
        このメソッドは単一レコードの変換に使用されます。

        Args:
            data: 変換元データ（dict形式を想定）

        Returns:
            StockPriceCreate: Pydanticモデル

        Raises:
            ValueError: データ形式が不正な場合
        """
        if not isinstance(data, dict):
            raise ValueError("data must be a dict")

        try:
            return StockPriceCreate(**data)
        except ValidationError as e:
            raise ValueError(f"Invalid data for StockPriceCreate: {e}") from e

    def from_pydantic(self, model: StockPriceCreate) -> Dict[str, Any]:
        """
        StockPriceCreate → DB保存用辞書変換

        Args:
            model: StockPriceCreateモデル

        Returns:
            dict[str, Any]: DB保存用の辞書

        Raises:
            ValueError: モデルが不正な場合
        """
        try:
            # Pydanticモデルを辞書に変換
            data_dict = model.model_dump()

            # タイムスタンプをUTCに変換（DB保存用）
            if isinstance(data_dict["trade_date"], datetime):
                data_dict["trade_date"] = data_dict["trade_date"].astimezone(
                    timezone.utc
                )

            # 不要なフィールドを除去（id, created_at, updated_atはDB側で管理）
            db_dict = {
                "symbol": data_dict["symbol"],
                "trade_date": data_dict["trade_date"],
                "open_price": data_dict["open_price"],
                "high": data_dict["high"],
                "low": data_dict["low"],
                "close": data_dict["close"],
                "volume": data_dict["volume"],
                "adj_close": data_dict["adj_close"],
            }

            return db_dict

        except Exception as e:
            logger.error(f"from_pydantic conversion error: {e}")
            raise ValueError(f"Failed to convert to dictionary: {e}") from e

    def from_dataframe(
        self, df: Any, *args, **kwargs
    ) -> List[StockPriceCreate]:
        """
        yfinance DataFrame → StockPriceCreateリスト変換

        Args:
            df: yfinanceから取得したDataFrame
            *args: 位置引数（symbol, timeframeの順）
            **kwargs: キーワード引数（symbol, timeframe）

        Returns:
            List[StockPriceCreate]: 株価データのリスト

        Raises:
            ValueError: データ変換に失敗した場合
        """
        # パラメータ取得
        symbol = args[0] if len(args) > 0 else kwargs.get("symbol")
        timeframe = args[1] if len(args) > 1 else kwargs.get("timeframe")

        if not symbol or not timeframe:
            raise ValueError("symbol and timeframe are required parameters")

        try:
            # データ検証
            self._validate_data(df)

            # タイムスタンプ正規化
            df_normalized = self._normalize_timestamps(df)

            # Pydanticモデルに変換
            stock_data_list = []
            for timestamp, row in df_normalized.iterrows():
                try:
                    stock_data = StockPriceCreate(
                        symbol=symbol,
                        trade_date=timestamp,
                        open_price=self._safe_float(row.get("Open")),
                        high=self._safe_float(row.get("High")),
                        low=self._safe_float(row.get("Low")),
                        close=self._safe_float(row.get("Close")),
                        volume=self._safe_int(row.get("Volume")),
                        adj_close=self._safe_float(row.get("Adj Close")),
                    )
                    stock_data_list.append(stock_data)
                except ValidationError as e:
                    logger.warning(
                        f"Data conversion error (symbol={symbol}, "
                        f"timestamp={timestamp}): {e}"
                    )
                    continue

            logger.info(
                f"Conversion completed: {len(stock_data_list)} items "
                f"(symbol={symbol})"
            )
            return stock_data_list

        except Exception as e:
            logger.error(
                f"from_dataframe conversion error (symbol={symbol}): {e}"
            )
            raise ValueError(f"Failed to convert stock price data: {e}") from e

    def _validate_data(self, df: pd.DataFrame) -> None:
        """
        DataFrameのデータ検証

        Args:
            df: 検証対象のDataFrame

        Raises:
            ValueError: 検証エラー
        """
        if df.empty:
            raise ValueError("DataFrameが空です")

        # 必須カラムの存在確認
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]
        if missing_columns:
            raise ValueError(f"必須カラムが不足しています: {missing_columns}")

        # データ型の確認
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("インデックスがDatetimeIndexではありません")

    def _normalize_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        タイムスタンプの正規化

        Args:
            df: 正規化対象のDataFrame

        Returns:
            正規化されたDataFrame
        """
        try:
            # インデックスがDatetimeIndexの場合
            if isinstance(df.index, pd.DatetimeIndex):
                # UTCに変換（タイムゾーン情報がない場合はUTCとみなす）
                if df.index.tz is None:
                    df_normalized = df.copy()
                    df_normalized.index = df_normalized.index.tz_localize(
                        "UTC"
                    )
                else:
                    df_normalized = df.copy()
                    df_normalized.index = df_normalized.index.tz_convert("UTC")
            else:
                raise ValueError("インデックスがDatetimeIndexではありません")

            return df_normalized

        except Exception as e:
            logger.error(f"Timestamp normalization error: {e}")
            raise ValueError(f"Failed to normalize timestamps: {e}") from e

    def _safe_float(self, value) -> Optional[float]:
        """
        安全なfloat変換

        Args:
            value: 変換対象の値

        Returns:
            float値またはNone
        """
        if pd.isna(value) or value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, value) -> Optional[int]:
        """
        安全なint変換

        Args:
            value: 変換対象の値

        Returns:
            int値またはNone
        """
        if pd.isna(value) or value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
