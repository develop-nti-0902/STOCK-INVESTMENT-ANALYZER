"""
サービス層コア抽象化モジュール.

全てのサービスが使用する共通抽象基底クラスとデコレータを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

from app.services.core.batch.base import BaseBatchRunner, BatchExecutionContext
from app.services.core.converters import BaseConverter
from app.services.core.decorators import handle_service_error, retry_on_error
from app.services.core.fetchers import BaseFetcher
from app.services.core.savers import BaseSaver
from app.services.core.validators import BaseValidator

__all__ = [
    "BaseFetcher",
    "BaseSaver",
    "BaseValidator",
    "BaseConverter",
    "handle_service_error",
    "retry_on_error",
    "BaseBatchRunner",
    "BatchExecutionContext",
]
