"""
API層 - 依存性注入プロバイダ

FastAPIのDependsパターンを使用したRepositoryとService提供を定義する。
共通モジュール（app.utils.database）のget_db()を使用してDBセッションを取得する。

仕様書: docs/architecture/layers/data_access_layer.md 3.3章
"""

from .auth import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
)
from .repositories import (
    get_base_repository,
    get_batch_execution_repository,
    get_stock_master_repository,
)
from .services import (
    get_stock_price_converter,
    get_stock_price_fetcher,
    get_stock_price_saver,
    get_stock_price_service,
    get_stock_price_validator,
)

__all__ = [
    "get_base_repository",
    "get_stock_master_repository",
    "get_batch_execution_repository",
    "get_stock_price_fetcher",
    "get_stock_price_converter",
    "get_stock_price_validator",
    "get_stock_price_saver",
    "get_stock_price_service",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
]
