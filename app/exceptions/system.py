"""例外処理モジュール - システム・設定関連例外.

システム設定、初期化、ユーティリティ機能に関連する例外クラスを定義します。
"""

from app.exceptions.base import AppException


class ConfigurationError(AppException):
    """設定エラーの基底例外クラス.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Configuration error occurred"
    default_error_code = "CONFIG_ERROR"
    default_status_code = 500


class SettingsValidationError(ConfigurationError):
    """設定値のバリデーションエラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Settings validation failed"
    default_error_code = "SETTINGS_VALIDATION_ERROR"
    default_status_code = 500


class EnvironmentVariableError(ConfigurationError):
    """環境変数が不足または不正な場合のエラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Required environment variable is missing or invalid"
    default_error_code = "ENV_VARIABLE_ERROR"
    default_status_code = 500


class FileSystemError(AppException):
    """ファイルシステム操作エラーの基底例外クラス.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "File system operation failed"
    default_error_code = "FILESYSTEM_ERROR"
    default_status_code = 500


class LoggingError(AppException):
    """ロギング設定・操作エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Logging operation failed"
    default_error_code = "LOGGING_ERROR"
    default_status_code = 500
