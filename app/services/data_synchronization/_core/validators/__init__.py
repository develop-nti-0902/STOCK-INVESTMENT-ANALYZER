"""
検証抽象化モジュール.

サービス層における共通検証の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.data_synchronization._core.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

__all__ = ["BaseValidator", "ValidationResult"]
