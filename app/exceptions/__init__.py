"""
例外処理モジュール

アプリケーション全体で使用するカスタム例外クラスとハンドラをエクスポートする。
仕様書: docs/architecture/layers/common_modules.md 3章
"""

# 基底例外
from app.exceptions.base import AppException

# ビジネスロジック関連例外
from app.exceptions.business import (
    BusinessError,
    CalculationError,
    InsufficientDataError,
)

# データベース関連例外
from app.exceptions.database import (
    ConstraintViolationError,
    DatabaseError,
    DuplicateRecordError,
    MasterDataError,
    RecordNotFoundError,
    StockDataError,
)

# 外部API関連例外
from app.exceptions.external_api import (
    APIRateLimitError,
    APITimeoutError,
    ExternalAPIError,
    JPXAPIError,
    YahooFinanceError,
)

# 例外ハンドラ
from app.exceptions.handlers import (
    app_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

# システム・設定関連例外
from app.exceptions.system import (
    ConfigurationError,
    EnvironmentVariableError,
    FileSystemError,
    LoggingError,
    SettingsValidationError,
)

# バリデーション関連例外
from app.exceptions.validation import (
    FieldValidationError,
    SchemaValidationError,
    ValidationError,
)

__all__ = [
    # 基底例外
    "AppException",
    # データベース関連
    "DatabaseError",
    "StockDataError",
    "MasterDataError",
    "ConstraintViolationError",
    "DuplicateRecordError",
    "RecordNotFoundError",
    # 外部API関連
    "ExternalAPIError",
    "YahooFinanceError",
    "JPXAPIError",
    "APITimeoutError",
    "APIRateLimitError",
    # バリデーション関連
    "ValidationError",
    "SchemaValidationError",
    "FieldValidationError",
    # ビジネスロジック関連
    "BusinessError",
    "InsufficientDataError",
    "CalculationError",
    # システム・設定関連
    "ConfigurationError",
    "SettingsValidationError",
    "EnvironmentVariableError",
    "FileSystemError",
    "LoggingError",
    # ハンドラ
    "app_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "general_exception_handler",
]
