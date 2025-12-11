from __future__ import annotations

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions.system import SettingsValidationError


class Settings(BaseSettings):
    """アプリケーション設定（環境変数管理）

    Pydantic Settings v2 を使用して環境変数から設定を読み込み、
    必要に応じて .env ファイルも参照します。
    """

    # アプリケーション基本設定
    APP_NAME: str = Field(..., description="Application name")
    APP_VERSION: str = Field(..., description="Application version")
    DEBUG: bool = Field(False, description="Debug flag")
    ENV: str = Field(
        "development",
        description="Environment identifier: development/production/test",
    )

    # データベース設定
    DB_HOST: str = Field(..., description="Database host")
    DB_PORT: int = Field(..., description="Database port")
    DB_NAME: str = Field(..., description="Database name")
    DB_USER: str = Field(..., description="Database user")
    DB_PASSWORD: str = Field(..., description="Database password")
    # 接続プール設定（環境変数で上書き可能）
    DB_POOL_SIZE: int = Field(
        5,
        description="SQLAlchemy engine pool size (default: 5)",
    )
    DB_MAX_OVERFLOW: int = Field(
        10,
        description="SQLAlchemy engine max overflow (default: 10)",
    )

    # ロギング設定
    LOG_LEVEL: str = Field("INFO", description="Log level")
    LOG_FILE: str = Field("app.log", description="Log file name/path")
    LOG_DIR: str = Field("logs", description="Log directory path")
    LOG_FORMAT: str = Field(
        "text",
        description="Log format: text or json",
    )
    LOG_MAX_BYTES: int = Field(
        10 * 1024 * 1024,
        description="Max log file size in bytes (default: 10MB)",
    )
    LOG_BACKUP_COUNT: int = Field(
        5,
        description="Number of backup log files to keep",
    )
    # Repository / API limits
    # 最大取得件数の上限値（例: get_recent やページネーションで使用）
    MAX_RECENT_LIMIT: int = Field(
        1000,
        description=(
            "Maximum number of records returned by get_recent-style " "queries"
        ),
    )

    # Yahoo Finance API設定
    YAHOO_FINANCE_TIMEOUT: int = Field(
        30,
        description="Yahoo Finance API timeout in seconds (default: 30)",
    )
    YAHOO_FINANCE_MAX_RETRIES: int = Field(
        3,
        description="Max retries for Yahoo Finance API calls (default: 3)",
    )
    YAHOO_FINANCE_RETRY_BACKOFF: float = Field(
        1.0,
        description="Backoff factor for retries (default: 1.0)",
    )
    YAHOO_FINANCE_CONCURRENCY_LIMIT: int = Field(
        10,
        description="Max concurrent requests (default: 10)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 未定義の環境変数は無視する
    )

    @property
    def is_production(self) -> bool:
        return str(self.ENV).lower() == "production"

    @property
    def is_development(self) -> bool:
        return str(self.ENV).lower() == "development"

    @property
    def is_test(self) -> bool:
        return str(self.ENV).lower() == "test"


def get_settings() -> Settings:
    """設定インスタンスを返す（カスタム例外でラップ）

    Returns:
        Settings: アプリケーション設定インスタンス

    Raises:
        SettingsValidationError: 設定値のバリデーションに失敗した場合
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        # Pydantic ValidationErrorをカスタム例外でラップ
        # エラー詳細を抽出
        error_details = {
            "errors": [
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ]
        }

        raise SettingsValidationError(
            message=(
                "Failed to load application settings. "
                "Please check your .env file and environment variables."
            ),
            context={"details": error_details, "original_error": exc},
        ) from exc
