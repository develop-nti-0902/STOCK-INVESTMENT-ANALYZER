"""例外処理モジュールのテスト - システム・設定関連例外."""

from app.exceptions.base import AppException
from app.exceptions.system import (
    ConfigurationError,
    EnvironmentVariableError,
    FileSystemError,
    LoggingError,
    SettingsValidationError,
)


class TestConfigurationError:
    """ConfigurationError基底クラスのテスト."""

    def test_default_initialization(self):
        """デフォルト値での初期化."""
        # Arrange: (特になし)

        # Act: デフォルト値でConfigurationErrorを初期化
        exc = ConfigurationError()

        # Assert: デフォルト値が正しく設定されていることを確認
        assert exc.message == "Configuration error occurred"
        assert exc.error_code == "CONFIG_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, AppException)

    def test_custom_message(self):
        """カスタムメッセージでの初期化."""
        # Arrange: (特になし)

        # Act: カスタムメッセージでConfigurationErrorを初期化
        exc = ConfigurationError(message="Custom config error")

        # Assert: カスタムメッセージが設定されていることを確認
        assert exc.message == "Custom config error"
        assert exc.error_code == "CONFIG_ERROR"


class TestSettingsValidationError:
    """SettingsValidationErrorのテスト."""

    def test_default_initialization(self):
        """デフォルト値での初期化."""
        # Arrange: (特になし)

        # Act: デフォルト値でSettingsValidationErrorを初期化
        exc = SettingsValidationError()

        # Assert: デフォルト値が正しく設定され、ConfigurationErrorを継承していることを確認
        assert exc.message == "Settings validation failed"
        assert exc.error_code == "SETTINGS_VALIDATION_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, ConfigurationError)

    def test_with_details(self):
        """詳細情報を含む初期化."""
        # Arrange: (特になし)

        # Act: 詳細情報を含めてSettingsValidationErrorを初期化
        exc = SettingsValidationError(
            message="Environment variable validation failed",
            context={
                "details": {
                    "errors": [
                        {
                            "field": "DB_HOST",
                            "message": "Field required",
                            "type": "missing",
                        }
                    ]
                }
            },
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Environment variable validation failed"
        assert "errors" in exc.details
        assert exc.details["errors"][0]["field"] == "DB_HOST"


class TestEnvironmentVariableError:
    """EnvironmentVariableErrorのテスト."""

    def test_default_initialization(self):
        """デフォルト値での初期化."""
        # Arrange: (特になし)

        # Act: デフォルト値でEnvironmentVariableErrorを初期化
        exc = EnvironmentVariableError()

        # Assert: デフォルト値が正しく設定され、ConfigurationErrorを継承していることを確認
        assert exc.message == "Required environment variable is missing or invalid"
        assert exc.error_code == "ENV_VARIABLE_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, ConfigurationError)

    def test_with_details(self):
        """詳細情報を含む初期化."""
        # Arrange: (特になし)

        # Act: 詳細情報を含めてEnvironmentVariableErrorを初期化
        exc = EnvironmentVariableError(
            message="Missing required environment variables",
            context={"details": {"missing_vars": ["DB_HOST", "DB_PORT"]}},
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Missing required environment variables"
        assert exc.details["missing_vars"] == ["DB_HOST", "DB_PORT"]


class TestFileSystemError:
    """FileSystemErrorのテスト."""

    def test_default_initialization(self):
        """デフォルト値での初期化."""
        # Arrange: (特になし)

        # Act: デフォルト値でFileSystemErrorを初期化
        exc = FileSystemError()

        # Assert: デフォルト値が正しく設定されていることを確認
        assert exc.message == "File system operation failed"
        assert exc.error_code == "FILESYSTEM_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, AppException)

    def test_with_details(self):
        """詳細情報を含む初期化."""
        # Arrange: (特になし)

        # Act: 詳細情報を含めてFileSystemErrorを初期化
        exc = FileSystemError(
            message="Failed to create log directory",
            context={
                "details": {
                    "path": "/var/log/app",
                    "operation": "mkdir",
                }
            },
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Failed to create log directory"
        assert exc.details["path"] == "/var/log/app"


class TestLoggingError:
    """LoggingErrorのテスト."""

    def test_default_initialization(self):
        """デフォルト値での初期化."""
        # Arrange: (特になし)

        # Act: デフォルト値でLoggingErrorを初期化
        exc = LoggingError()

        # Assert: デフォルト値が正しく設定されていることを確認
        assert exc.message == "Logging operation failed"
        assert exc.error_code == "LOGGING_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, AppException)

    def test_with_details(self):
        """詳細情報を含む初期化."""
        # Arrange: (特になし)

        # Act: 詳細情報を含めてLoggingErrorを初期化
        exc = LoggingError(
            message="Failed to initialize logger",
            context={
                "details": {
                    "logger_name": "app.main",
                    "handler": "RotatingFileHandler",
                }
            },
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Failed to initialize logger"
        assert exc.details["logger_name"] == "app.main"
