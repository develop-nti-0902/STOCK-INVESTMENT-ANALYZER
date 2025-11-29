from __future__ import annotations

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # ロギング設定
    LOG_LEVEL: str = Field("INFO", description="Log level")
    LOG_FILE: str = Field("app.log", description="Log file name/path")

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
    """設定インスタンスを返す（必要に応じて例外を標準化）"""
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        # ここで例外をそのまま上げる。例外モジュール統合時にラップ可能。
        raise exc
