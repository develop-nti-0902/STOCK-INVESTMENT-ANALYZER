"""
例外処理モジュール - システム・設定関連例外

システム設定、初期化、ユーティリティ機能に関連する例外クラスを定義する。
"""

from typing import Optional

from app.exceptions.base import AppException


class ConfigurationError(AppException):
    """設定エラーの基底例外クラス"""

    def __init__(
        self,
        *,
        message: str = "Configuration error occurred",
        error_code: str = "CONFIG_ERROR",
        status_code: int = 500,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            original_error=original_error,
        )


class SettingsValidationError(ConfigurationError):
    """設定値のバリデーションエラー"""

    def __init__(
        self,
        *,
        message: str = "Settings validation failed",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="SETTINGS_VALIDATION_ERROR",
            status_code=500,
            details=details,
            original_error=original_error,
        )


class EnvironmentVariableError(ConfigurationError):
    """環境変数が不足または不正な場合のエラー"""

    def __init__(
        self,
        *,
        message: str = "Required environment variable is missing or invalid",
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="ENV_VARIABLE_ERROR",
            status_code=500,
            details=details,
            original_error=original_error,
        )


class FileSystemError(AppException):
    """ファイルシステム操作エラーの基底例外クラス"""

    def __init__(
        self,
        *,
        message: str = "File system operation failed",
        error_code: str = "FILESYSTEM_ERROR",
        status_code: int = 500,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            original_error=original_error,
        )


class LoggingError(AppException):
    """ロギング設定・操作エラー"""

    def __init__(
        self,
        *,
        message: str = "Logging operation failed",
        error_code: str = "LOGGING_ERROR",
        status_code: int = 500,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
            original_error=original_error,
        )
