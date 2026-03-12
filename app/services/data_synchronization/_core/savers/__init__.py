"""
データ保存抽象化モジュール.

サービス層におけるデータ保存の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.data_synchronization._core.savers.base_saver import BaseSaver
from app.services.data_synchronization._core.savers.bulk_saver_mixin import BulkSaverMixin

__all__ = ["BaseSaver", "BulkSaverMixin"]
