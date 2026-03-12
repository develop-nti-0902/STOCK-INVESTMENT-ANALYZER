"""
パーサー抽象化モジュール.

サービス層における共通パーサーの抽象基底クラスを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.data_synchronization._core.parsers.base_parser import BaseParser
from app.services.data_synchronization._core.parsers.xml_parser_mixin import XMLParserMixin

__all__ = ["BaseParser", "XMLParserMixin"]
