"""
データ保存抽象化モジュール

サービス層におけるデータ保存の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.core.savers.base_saver import BaseSaver

__all__ = ["BaseSaver"]
