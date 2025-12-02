"""
データ取得抽象化モジュール

サービス層における外部データ取得の抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.core.fetchers.base_fetcher import BaseFetcher

__all__ = ["BaseFetcher"]
