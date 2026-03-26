"""日経225データ検証モジュール."""

from __future__ import annotations

from typing import Any

from app.services.data_synchronization._core.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei225Validator(BaseValidator):
    """日経225データバリデーター（バイパス実装）.

    現状は yfinance の生データをそのまま利用するためバイパス。
    将来的に OHLC 整合性チェック等を追加する拡張ポイント。
    """

    def validate(self, data: Any) -> ValidationResult:
        """バイパス実装: 常に成功を返す.

        Args:
            data: 検証対象データ（未使用）

        Returns:
            ValidationResult: 常に成功
        """
        logger.debug("Nikkei225Validator.validate bypassed")
        return ValidationResult(True, [], ["Validation bypassed; using yfinance raw data"])
