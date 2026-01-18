"""
株価データ変換層

yfinance DataFrameをPydanticモデルに変換し、さらにDB保存用の辞書形式に変換する機能を提供します。
仕様書: docs/architecture/layers/service_layer.md 3.2.2章
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import ValidationError

from app.exceptions.business import ServiceError
from app.exceptions.validation import FieldValidationError
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
            raise ServiceError(message="data must be a dict")

        try:
            return StockPriceCreate(**data)
        except ValidationError as e:
            raise ServiceError(
                message=f"Invalid data for StockPriceCreate: {e}"
            ) from e

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

            # trade_date はそのまま保持（プロジェクトではJSTを前提とする）
            # 変換は行わない

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
            raise ServiceError(
                message=f"Failed to convert to dictionary: {e}"
            ) from e

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
            raise FieldValidationError(
                message="symbol and timeframe are required parameters"
            )

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
                        "Data conversion error (symbol=%s, "
                        "timestamp=%s): %s",
                        symbol,
                        timestamp,
                        e,
                    )
                    continue

            logger.info(
                "Conversion completed: %d items " "(symbol=%s)",
                len(stock_data_list),
                symbol,
            )
            return stock_data_list

        except Exception as e:
            logger.error(
                "from_dataframe conversion error " "(symbol=%s): %s",
                symbol,
                e,
            )
            raise ServiceError(
                message=f"Failed to convert stock price data: {e}"
            ) from e

    def _validate_data(self, df: pd.DataFrame) -> None:
        """
        DataFrameのデータ検証

        Args:
            df: 検証対象のDataFrame

        Raises:
            ValueError: 検証エラー
        """
        if df.empty:
            raise ServiceError(message="DataFrameが空です")

        # 必須カラムの存在確認
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]
        if missing_columns:
            raise ServiceError(
                message=f"必須カラムが不足しています: {missing_columns}"
            )

        # データ型の確認
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ServiceError(
                message="インデックスがDatetimeIndexではありません"
            )

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
                # JST (Asia/Tokyo) を前提とする
                if df.index.tz is None:
                    df_normalized = df.copy()
                    df_normalized.index = df_normalized.index.tz_localize(
                        "Asia/Tokyo"
                    )
                else:
                    df_normalized = df.copy()
                    df_normalized.index = df_normalized.index.tz_convert(
                        "Asia/Tokyo"
                    )
            else:
                raise ServiceError(
                    message="インデックスがDatetimeIndexではありません"
                )

            return df_normalized

        except Exception as e:
            logger.error(f"Timestamp normalization error: {e}")
            raise ServiceError(
                message=f"Failed to normalize timestamps: {e}"
            ) from e

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

    def to_saver_record(self, model: StockPriceCreate) -> Dict[str, Any]:
        """
        StockPriceCreate -> Saver入力用辞書に変換します。

        Args:
            model: StockPriceCreateモデル

        Returns:
            Dict[str, Any]: Saverが期待するフィールド一覧
                - timestamp
                - open, high, low, close, volume, adj_close
        """
        data = model.model_dump()
        return {
            "timestamp": data.get("trade_date"),
            "open": data.get("open_price"),
            "high": data.get("high"),
            "low": data.get("low"),
            "close": data.get("close"),
            "volume": data.get("volume"),
            "adj_close": data.get("adj_close"),
        }

    def to_saver_records(
        self, models: List[StockPriceCreate]
    ) -> List[Dict[str, Any]]:
        """
        複数の StockPriceCreate を Saver 用の辞書リストに変換します。
        """
        return [self.to_saver_record(m) for m in models]
