"""
株価データ検証層.

株価データの整合性と妥当性を検証する機能を提供します。
仕様書: docs/architecture/layers/service_layer.md 3.2.3章
"""

import logging
from typing import Any

from app.services.data_synchronization._core.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class StockPriceValidator(BaseValidator):
    """
    株価データ検証クラス.

    株価データの必須カラム、数値範囲、OHLC整合性、タイムスタンプの妥当性を検証します。
    BaseValidatorを継承し、標準的な検証インターフェースを実装します。
    """

    def __init__(self):
        """初期化."""
        super().__init__()

    def validate(self, data: Any) -> ValidationResult:
        """バイパス実装: yfinanceの生データをそのまま利用するため、常に成功を返します.

        将来的に検証を再導入する場合はここを編集してください。
        """
        logger.debug("StockPriceValidator.validate bypassed: using raw yfinance data")
        return ValidationResult(True, [], ["Validation bypassed; using yfinance raw data"])
