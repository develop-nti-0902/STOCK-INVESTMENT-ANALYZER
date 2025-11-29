import importlib
import sys

import pytest
from pydantic import ValidationError


def test_settings_env_only_returns_expected_values(monkeypatch):
    """
    環境変数のみで設定値が正しく取得できることを検証する
    （.envファイルがなくても動作することを含む）
    """
    # Arrange
    monkeypatch.setenv("APP_NAME", "SIA")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("ENV", "development")

    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "stockdb")
    monkeypatch.setenv("DB_USER", "stock_user")
    monkeypatch.setenv("DB_PASSWORD", "password")

    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_FILE", "app.log")

    # Act
    sys.modules.pop("app.utils.config", None)
    config_module = importlib.import_module("app.utils.config")
    settings = config_module.get_settings()

    # Assert
    assert settings.APP_NAME == "SIA"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.DEBUG is True
    assert settings.is_development is True

    assert settings.DB_HOST == "localhost"
    assert settings.DB_PORT == 5432
    assert settings.DB_NAME == "stockdb"
    assert settings.DB_USER == "stock_user"
    assert settings.DB_PASSWORD == "password"

    assert settings.LOG_LEVEL == "INFO"
    assert settings.LOG_FILE == "app.log"


def test_settings_missing_required_env_raises_validation_error(monkeypatch):
    """
    必須環境変数が未設定の場合にValidationErrorが発生し、
    エラーメッセージに不足変数名が含まれることを検証する
    """
    # Arrange: 必須環境変数をすべて削除
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

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
    """
    ENVがproductionの場合、is_productionがTrueを返すことを検証する
    """
    # Arrange
    monkeypatch.setenv("APP_NAME", "SIA")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "stockdb")
    monkeypatch.setenv("DB_USER", "stock_user")
    monkeypatch.setenv("DB_PASSWORD", "password")

    # Act
    sys.modules.pop("app.utils.config", None)
    config_module = importlib.import_module("app.utils.config")
    settings = config_module.get_settings()

    # Assert
    assert settings.is_production is True
    assert settings.is_development is False
    assert settings.is_test is False


def test_settings_is_test_returns_true_when_env_is_test(monkeypatch):
    """
    ENVがtestの場合、is_testがTrueを返すことを検証する
    """
    # Arrange
    monkeypatch.setenv("APP_NAME", "SIA")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("ENV", "test")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")
    monkeypatch.setenv("DB_NAME", "stockdb")
    monkeypatch.setenv("DB_USER", "stock_user")
    monkeypatch.setenv("DB_PASSWORD", "password")

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
):
    """
    get_settings()関数が必須環境変数未設定時にValidationErrorを送出することを検証する
    （exceptブロックのカバレッジ向上）
    """
    # Arrange: 必須環境変数を削除
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_VERSION", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)

    # Act & Assert: get_settings()がValidationErrorを送出することを確認
    # 注意: モジュールキャッシュをクリアして環境変数の変更を反映
    sys.modules.pop("app.utils.config", None)

    # get_settings()を直接呼び出し、exceptブロックを通過させる
    # monkeypatchでget_settingsをモック化してexceptパスをカバー
    # pylint: disable=import-outside-toplevel
    from unittest.mock import patch

    from app.utils.config import Settings

    with patch.object(
        Settings,
        "__init__",
        side_effect=ValidationError.from_exception_data(
            "test", [{"type": "missing", "loc": ("APP_NAME",), "input": {}}]
        ),
    ):
        with pytest.raises(ValidationError):
            from app.utils.config import get_settings  # noqa: F401

            get_settings()
