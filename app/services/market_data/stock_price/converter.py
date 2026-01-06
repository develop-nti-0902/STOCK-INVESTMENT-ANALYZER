"""
株価データ変換層

yfinance DataFrameをPydanticモデルに変換し、さらにDB保存用の辞書形式に変換する機能を提供します。
仕様書: docs/architecture/layers/service_layer.md 3.2.2章
"""

import logging
from typing import Any, Dict, List

import pandas as pd

from app.exceptions.business import ServiceError
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
        現状は継承不要なので未実装
        """
        raise NotImplementedError(
            "to_pydantic is not implemented for StockPriceConverter."
            " Implement when needed."
        )

    def from_pydantic(self, model: StockPriceCreate) -> Dict[str, Any]:
        """
        現状は継承不要なので未実装
        """
        raise NotImplementedError(
            "from_pydantic is not implemented for StockPriceConverter."
            " Implement when needed."
        )

    def from_dataframe(
        self, df: Any, *args, **kwargs
    ) -> List[StockPriceCreate]:
        """
        現状は継承不要なので未実装
        """
        raise NotImplementedError(
            "from_dataframe is not implemented for StockPriceConverter."
            " Implement when needed."
        )

    def _validate_data(self, df: pd.DataFrame) -> None:
        """
        DataFrameのデータ検証

        Args:
            df: 検証対象のDataFrame

        Raises:
            ValueError: 検証エラー
        """
        if df.empty:
            raise ServiceError(message="DataFrame is empty")

        # 必須カラムの存在確認
        required_columns = ["Open", "High", "Low", "Close", "Volume"]
        missing_columns = [
            col for col in required_columns if col not in df.columns
        ]
        if missing_columns:
            raise ServiceError(
                message=f"Missing required columns: {missing_columns}"
            )

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
