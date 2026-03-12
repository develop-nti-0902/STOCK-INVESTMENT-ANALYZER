"""
データ変換抽象化モジュール.

サービス層におけるデータ変換の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.data_synchronization._core.converters.base_converter import BaseConverter

__all__ = ["BaseConverter"]
