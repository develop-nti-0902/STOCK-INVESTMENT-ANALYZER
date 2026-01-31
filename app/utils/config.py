from __future__ import annotations

from typing import Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions.system import SettingsValidationError


class BatchProcessingSettings(BaseSettings):
    """バッチ処理関連の設定.

    Attributes:
        batch_size (int): バッチあたりの処理対象数.
        max_concurrent (int): 同時実行タスク数の上限.
        retry_attempts (int): リトライ試行回数.
        retry_delay (float): リトライ間の遅延（秒）.
        request_timeout (int): HTTP リクエストタイムアウト（秒）.
        operation_timeout (int): 全体操作のタイムアウト（秒）.
        rate_limit_calls (int): 指定期間内の API 呼び出し上限.
        rate_limit_period (int): レート制限の時間窓（秒）.
    """

    # バッチサイズ
    batch_size: int = Field(
        default=100, ge=1, le=1000, description="Number of symbols per batch"
    )

    # 並列実行数（同時処理銘柄数）
    max_concurrent: int = Field(
        default=20, ge=1, le=100, description="Maximum concurrent tasks"
    )

    # リトライ設定
    retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retry attempts on failure",
    )

    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Delay between retries in seconds",
    )

    # タイムアウト設定
    request_timeout: int = Field(
        default=30, ge=5, le=300, description="HTTP request timeout in seconds"
    )

    operation_timeout: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Overall operation timeout in seconds",
    )

    # レート制限設定
    rate_limit_calls: int = Field(
        default=2000, ge=1, le=10000, description="API calls per time window"
    )

    rate_limit_period: int = Field(
        default=3600,
        ge=60,
        le=86400,
        description="Rate limit time window in seconds",
    )

    model_config = SettingsConfigDict(
        env_prefix="BATCH_",
        env_file=".env",
        extra="ignore",
    )


class Settings(BaseSettings):
    """アプリケーション設定（環境変数から読み込み）.

    Pydantic Settings v2 を利用して設定を読み込みます。必要に応じて
    ``.env`` ファイルも参照します。

    Attributes:
        APP_NAME (str): アプリケーション名.
        APP_VERSION (str): アプリケーションのバージョン.
        DEBUG (bool): デバッグフラグ.
        ENV (str): 実行環境識別子（development/production/test）.
        batch (BatchProcessingSettings): バッチ処理関連のネスト設定.
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

    # CORS設定: 開発時は localhost をデフォルトで許可する
    CORS_ALLOW_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        description=(
            "Allowed origins for CORS. In environment variables, "
            "provide a comma-separated list"
        ),
    )

    CORS_ALLOW_CREDENTIALS: bool = Field(
        True, description="Whether to allow credentials in CORS responses"
    )

    CORS_ALLOW_METHODS: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP methods for CORS",
    )

    CORS_ALLOW_HEADERS: list[str] = Field(
        default_factory=lambda: ["*"],
        description="Allowed HTTP headers for CORS",
    )

    # EDINET API 設定
    # - サービスによっては Subscription-Key が必要になるため環境変数で管理します
    EDINET_SUBSCRIPTION_KEY: Optional[str] = Field(
        None, description="Subscription key for EDINET API (if required)"
    )

    # バッチ処理設定
    batch: BatchProcessingSettings = Field(
        default_factory=BatchProcessingSettings
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
