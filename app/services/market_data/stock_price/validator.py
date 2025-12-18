"""
株価データ検証層

株価データの整合性と妥当性を検証する機能を提供します。
仕様書: docs/architecture/layers/service_layer.md 3.2.3章
"""

import logging
from datetime import datetime
from typing import Any, List

from app.services.core.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class StockPriceValidator(BaseValidator):
    """
    株価データ検証クラス

    株価データの必須カラム、数値範囲、OHLC整合性、タイムスタンプの妥当性を検証します。
    BaseValidatorを継承し、標準的な検証インターフェースを実装します。
    """

    def __init__(self):
        """初期化"""
        super().__init__()

    def validate(self, data: Any) -> ValidationResult:
        """
        株価データを検証します。

        Args:
            data: 検証対象のデータ（dict, Pydanticモデル, DataFrameなど）

        Returns:
            ValidationResult: 検証結果
        """
        errors = []
        warnings = []

        try:
            # データ形式のチェック
            if isinstance(data, dict):
                validated_data = data
            elif hasattr(data, "model_dump"):
                # Pydanticモデル
                validated_data = data.model_dump()
            else:
                errors.append("Unsupported data format")
                return ValidationResult(False, errors, warnings)

            # 必須カラムの存在確認
            required_fields = [
                "symbol",
                "trade_date",
                "open_price",
                "high",
                "low",
                "close",
                "volume",
            ]
            missing_fields = [
                field
                for field in required_fields
                if field not in validated_data
            ]
            if missing_fields:
                errors.append(f"Required fields are missing: {missing_fields}")

            # 各フィールドの検証
            if "symbol" in validated_data:
                symbol_errors = self._validate_symbol(validated_data["symbol"])
                errors.extend(symbol_errors)

            if "trade_date" in validated_data:
                date_errors = self._validate_trade_date(
                    validated_data["trade_date"]
                )
                errors.extend(date_errors)

            # OHLCデータの検証
            ohlc_fields = ["open_price", "high", "low", "close"]
            if all(field in validated_data for field in ohlc_fields):
                ohlc_errors = self._validate_ohlc_data(
                    validated_data["open_price"],
                    validated_data["high"],
                    validated_data["low"],
                    validated_data["close"],
                )
                errors.extend(ohlc_errors)

            # Volumeの検証
            if "volume" in validated_data:
                volume_errors = self._validate_volume(validated_data["volume"])
                errors.extend(volume_errors)

            # 数値フィールドの範囲検証
            numeric_fields = [
                "open_price",
                "high",
                "low",
                "close",
                "adj_close",
            ]
            for field in numeric_fields:
                if (
                    field in validated_data
                    and validated_data[field] is not None
                ):
                    range_errors = self._validate_numeric_range(
                        field, validated_data[field]
                    )
                    errors.extend(range_errors)

        except Exception as e:
            errors.append(
                f"Unexpected error occurred during validation: {str(e)}"
            )
            logger.exception("Stock price validation error")

        return ValidationResult(len(errors) == 0, errors, warnings)

    def _validate_symbol(self, symbol: Any) -> List[str]:
        """銘柄コードの検証"""
        errors = []

        if symbol is None:
            errors.append("symbol is required")
            return errors

        if not symbol.strip():
            errors.append("symbol cannot be an empty string")

        # 銘柄コードの形式チェック（例: 4桁の数字 + .T など）
        # 必要に応じて拡張

        return errors

    def _validate_trade_date(self, trade_date: Any) -> List[str]:
        """取引日時の検証"""
        errors = []

        if trade_date is None:
            errors.append("trade_date is required")
            return errors

        # 未来日のチェック（オプション）
        if isinstance(trade_date, datetime):
            now = (
                datetime.now(trade_date.tzinfo)
                if trade_date.tzinfo
                else datetime.now()
            )
            if trade_date > now:
                errors.append("trade_date cannot be in the future")

        return errors

    def _validate_ohlc_data(
        self, open_price: Any, high: Any, low: Any, close: Any
    ) -> List[str]:
        """OHLCデータの整合性検証"""
        errors = []

        prices = [open_price, high, low, close]

        # Noneチェック
        if any(price is None for price in prices):
            return errors  # Noneは許容（欠損値）

        # OHLC整合性チェック
        if not (low <= open_price <= high):
            errors.append(
                "Open price must be within the range of high and low prices"
            )

        if not (low <= close <= high):
            errors.append(
                "Close price must be within the range of high and low prices"
            )

        return errors

    def _validate_volume(self, volume: Any) -> List[str]:
        """出来高の検証"""
        errors = []

        if volume is None:
            return errors  # Noneは許容

        if volume < 0:
            errors.append("volume must be greater than or equal to 0")

        return errors

    def _validate_numeric_range(
        self, field_name: str, value: Any
    ) -> List[str]:
        """数値フィールドの範囲検証"""
        errors = []

        if value is None:
            return errors

        # 価格データの負数チェック
        if "price" in field_name.lower() and value < 0:
            errors.append(f"{field_name} must be greater than or equal to 0")

        return errors
