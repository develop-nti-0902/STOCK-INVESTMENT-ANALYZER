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
        """バイパス実装: yfinanceの生データをそのまま利用するため、常に成功を返します。

        将来的に検証を再導入する場合はここを編集してください。
        """
        logger.debug(
            "StockPriceValidator.validate bypassed: using raw yfinance data"
        )
        return ValidationResult(
            True, [], ["Validation bypassed; using yfinance raw data"]
        )

    def _validate_symbol(self, symbol: Any) -> List[str]:
        """銘柄コードの検証"""
        errors: List[str] = []

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
        errors: List[str] = []

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
        errors: List[str] = []

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
        errors: List[str] = []

        if volume is None:
            return errors  # Noneは許容

        if volume < 0:
            errors.append("volume must be greater than or equal to 0")

        return errors

    def _validate_numeric_range(
        self, field_name: str, value: Any
    ) -> List[str]:
        """数値フィールドの範囲検証"""
        errors: List[str] = []

        if value is None:
            return errors

        # 価格データの負数チェック
        if "price" in field_name.lower() and value < 0:
            errors.append(f"{field_name} must be greater than or equal to 0")

        return errors
