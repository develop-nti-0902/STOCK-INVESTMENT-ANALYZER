"""`app.utils.config` の単体テスト。テスト関数名で動作を説明しています."""

import importlib
import sys

import pytest
from pydantic import ValidationError


def test_settings_env_only_returns_expected_values(monkeypatch):
    """環境変数のみで設定値が正しく取得できることを検証する."""
    # Arrange
    monkeypatch.setenv("APP_NAME", "SIA")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ENV", "development")

    # Use DATABASE_URL for connection in tests (no Postgres-specific vars)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FILE", "app.log")
    # EDINET APIキーはSettingsで必須になったためテスト用のダミー値を設定
    monkeypatch.setenv("EDINET_SUBSCRIPTION_KEY", "dummy_key")

    # Act
    sys.modules.pop("app.utils.config", None)
    config_module = importlib.import_module("app.utils.config")
    settings = config_module.get_settings()

    # Assert
    assert settings.APP_NAME == "SIA"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.DEBUG is True
    assert settings.is_development is True

    assert settings.DATABASE_URL == "sqlite:///test.db"

    assert settings.LOG_LEVEL == "INFO"
    assert settings.LOG_FILE == "app.log"


def test_settings_missing_required_env_raises_validation_error(monkeypatch):
    """必須環境変数未設定時に ValidationError が発生することを検証する."""
    # Arrange: 必須環境変数をすべて削除
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Act & Assert: .envファイルを読み込まずにSettingsをインスタンス化
    # 注意: sys.modules.pop()でモジュールキャッシュをクリアし、
    # monkeypatchで変更した環境変数が確実に反映されるようにする。
    # その直後にimportすることで、クリア→再インポートの流れを明示。
    sys.modules.pop("app.utils.config", None)
    # pylint: disable=import-outside-toplevel
    from app.utils.config import Settings

    # _env_file=Noneを指定することで、.envファイルからの読み込みをスキップし、
    # 環境変数が未設定の状態を確実に再現してValidationErrorを発生させる。
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    # エラーメッセージに不足している必須変数が含まれることを確認
    error_message = str(exc_info.value)
    assert "APP_NAME" in error_message or "app_name" in error_message


def test_settings_is_production_returns_true_when_env_is_production(
    monkeypatch,
):
    """ENV が production のとき is_production を True と判定することを検証する."""
    # Arrange
    monkeypatch.setenv("APP_NAME", "SIA")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    # EDINET APIキーはSettingsで必須になったためテスト用のダミー値を設定
    monkeypatch.setenv("EDINET_SUBSCRIPTION_KEY", "dummy_key")

    # Act
    sys.modules.pop("app.utils.config", None)
    config_module = importlib.import_module("app.utils.config")
    settings = config_module.get_settings()

    # Assert
    assert settings.is_production is True
    assert settings.is_development is False
    assert settings.is_test is False


def test_settings_is_test_returns_true_when_env_is_test(monkeypatch):
    """ENV が test のとき is_test を True と判定することを検証する."""
    # Arrange
    monkeypatch.setenv("APP_NAME", "SIA")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    # EDINET APIキーはSettingsで必須になったためテスト用のダミー値を設定
    monkeypatch.setenv("EDINET_SUBSCRIPTION_KEY", "dummy_key")

    # Act
    sys.modules.pop("app.utils.config", None)
    config_module = importlib.import_module("app.utils.config")
    settings = config_module.get_settings()

    # Assert
    assert settings.is_test is True
    assert settings.is_production is False
    assert settings.is_development is False


def test_get_settings_raises_validation_error_when_required_env_missing(
    monkeypatch,
    tmp_path,
):
    """get_settings() が必須環境変数未設定時に SettingsValidationError を送出することを検証する."""
    # Arrange: キャッシュをクリアして環境変数を削除
    sys.modules.pop("app.utils.config", None)
    sys.modules.pop("app.exceptions.system", None)

    # 必須環境変数を削除
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # .envファイルを読み込まないように一時ディレクトリに移動
    monkeypatch.chdir(tmp_path)

    # Act & Assert: get_settings()がSettingsValidationErrorを送出することを確認
    # pylint: disable=import-outside-toplevel
    from app.exceptions.system import SettingsValidationError
    from app.utils.config import get_settings

    with pytest.raises(SettingsValidationError) as exc_info:
        get_settings()

    # カスタム例外の属性を検証
    assert exc_info.value.error_code == "SETTINGS_VALIDATION_ERROR"
    assert "errors" in exc_info.value.details
    assert len(exc_info.value.details["errors"]) > 0
    assert isinstance(exc_info.value.original_error, ValidationError)


def test_batch_processing_settings_default_values():
    """BatchProcessingSettings のデフォルト値を検証する."""
    # Arrange & Act
    from app.utils.config import BatchProcessingSettings

    settings = BatchProcessingSettings()

    # Assert
    assert settings.batch_size == 100
    assert settings.max_concurrent == 20
    assert settings.retry_attempts == 3
    assert settings.retry_delay == 1.0
    assert settings.request_timeout == 30
    assert settings.operation_timeout == 3600
    assert settings.rate_limit_calls == 2000
    assert settings.rate_limit_period == 3600


def test_batch_processing_settings_env_variables(monkeypatch):
    """BatchProcessingSettings が環境変数から読み込まれることを検証する."""
    # Arrange
    monkeypatch.setenv("BATCH_BATCH_SIZE", "50")
    monkeypatch.setenv("BATCH_MAX_CONCURRENT", "10")
    monkeypatch.setenv("BATCH_RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("BATCH_RETRY_DELAY", "2.0")
    monkeypatch.setenv("BATCH_REQUEST_TIMEOUT", "60")
    monkeypatch.setenv("BATCH_OPERATION_TIMEOUT", "7200")
    monkeypatch.setenv("BATCH_RATE_LIMIT_CALLS", "1000")
    monkeypatch.setenv("BATCH_RATE_LIMIT_PERIOD", "1800")

    # Act
    from app.utils.config import BatchProcessingSettings

    settings = BatchProcessingSettings()

    # Assert
    assert settings.batch_size == 50
    assert settings.max_concurrent == 10
    assert settings.retry_attempts == 5
    assert settings.retry_delay == 2.0
    assert settings.request_timeout == 60
    assert settings.operation_timeout == 7200
    assert settings.rate_limit_calls == 1000
    assert settings.rate_limit_period == 1800


def test_batch_processing_settings_validation():
    """BatchProcessingSettings のバリデーションを検証する."""
    from pydantic import ValidationError

    from app.utils.config import BatchProcessingSettings

    # バッチサイズの最小値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(batch_size=0)

    # バッチサイズの最大値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(batch_size=1001)

    # 並列実行数の最小値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(max_concurrent=0)

    # 並列実行数の最大値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(max_concurrent=101)

    # リトライ回数の最小値検証（0は許可）
    settings = BatchProcessingSettings(retry_attempts=0)
    assert settings.retry_attempts == 0

    # リトライ回数の最大値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(retry_attempts=11)

    # リトライ遅延の最小値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(retry_delay=0.05)

    # リトライ遅延の最大値検証
    with pytest.raises(ValidationError):
        BatchProcessingSettings(retry_delay=65.0)


def test_settings_includes_batch_processing_settings():
    """Settings が BatchProcessingSettings を包含していることを検証する."""
    # Arrange
    import os

    os.environ["BATCH_BATCH_SIZE"] = "75"
    os.environ["BATCH_MAX_CONCURRENT"] = "15"
    # EDINET APIキーはSettingsで必須になったためテスト用のダミー値を設定
    os.environ["EDINET_SUBSCRIPTION_KEY"] = "dummy_key"

    try:
        # Act
        from app.utils.config import get_settings

        settings = get_settings()

        # Assert
        assert hasattr(settings, "batch")
        assert settings.batch.batch_size == 75
        assert settings.batch.max_concurrent == 15
        assert settings.batch.retry_attempts == 3  # デフォルト値

    finally:
        # Cleanup
        del os.environ["BATCH_BATCH_SIZE"]
        del os.environ["BATCH_MAX_CONCURRENT"]
        del os.environ["EDINET_SUBSCRIPTION_KEY"]
