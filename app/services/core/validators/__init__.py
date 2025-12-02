"""
データ検証抽象化モジュール

サービス層におけるデータ検証の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.core.validators.base_validator import BaseValidator

__all__ = ["BaseValidator"]
