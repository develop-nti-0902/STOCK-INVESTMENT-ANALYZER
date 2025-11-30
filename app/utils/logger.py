"""ロガー設定モジュール

統一されたログ出力機能を提供します。
- 構造化ログ出力（JSON形式対応）
- ログレベル制御（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- ファイル出力とコンソール出力の両立
- ログローテーション設定
- リクエストID付与（トレーサビリティ）
- タイムスタンプ・ログレベル・モジュール名の自動付与
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional

from app.exceptions.system import SettingsValidationError
from app.utils.config import get_settings

# =============================================================================
# モジュールレベル変数
# =============================================================================

# リクエストIDを格納するコンテキスト変数
request_id_var: ContextVar[Optional[str]] = ContextVar(
    "request_id", default=None
)


# =============================================================================
# クラス定義
# =============================================================================


class StructuredFormatter(logging.Formatter):
    """構造化ログフォーマッタ

    JSON形式のログ出力をサポートします。
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        use_json: bool = False,
    ) -> None:
        """初期化

        Args:
            fmt: ログフォーマット文字列
            datefmt: 日時フォーマット文字列
            use_json: JSON形式で出力するかどうか
        """
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.use_json = use_json

    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをフォーマット

        Args:
            record: ログレコード

        Returns:
            フォーマット済みのログメッセージ
        """
        if self.use_json:
            return self._format_json(record)

        return self._format_text(record)

    def _format_json(self, record: logging.LogRecord) -> str:
        """JSON形式でログレコードをフォーマット

        Args:
            record: ログレコード

        Returns:
            JSON形式のログメッセージ
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # リクエストIDが存在する場合は追加
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        # 追加の属性がある場合
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra  # type: ignore[attr-defined]

        # 例外情報がある場合
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)

    def _format_text(self, record: logging.LogRecord) -> str:
        """テキスト形式でログレコードをフォーマット

        Args:
            record: ログレコード

        Returns:
            テキスト形式のログメッセージ
        """
        timestamp = datetime.fromtimestamp(
            record.created, tz=timezone.utc
        ).isoformat()
        request_id = request_id_var.get()
        request_id_str = f" [{request_id}]" if request_id else ""
        message = record.getMessage()

        log_line = (
            f"[{timestamp}] [{record.levelname}]{request_id_str} "
            f"[{record.name}] {message}"
        )

        # 例外情報がある場合は追加
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)

        return log_line


class _DefaultLogger:
    """デフォルトロガーのシングルトンホルダー

    グローバル変数を使わずに遅延初期化を実現します。
    """

    _instance: Optional[logging.Logger] = None

    @classmethod
    def get(cls) -> logging.Logger:
        """デフォルトロガーを取得（遅延初期化）

        Returns:
            デフォルトロガー
        """
        if cls._instance is None:
            cls._instance = setup_logger("app")
        return cls._instance


# =============================================================================
# ロガーセットアップ関数
# =============================================================================


def setup_logger(
    name: str = __name__,
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    use_json: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Logger:
    # pylint: disable=too-many-arguments,too-many-locals
    # pylint: disable=too-many-positional-arguments
    """ロガーをセットアップ

    Args:
        name: ロガー名（通常はモジュール名）
        log_level: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
        log_file: ログファイル名
        log_dir: ログファイルディレクトリ
        use_json: JSON形式で出力するかどうか
        max_bytes: ログファイルの最大サイズ（バイト）
        backup_count: バックアップファイル数

    Returns:
        設定済みのロガー
    """
    # 設定を取得（失敗時はデフォルト値を使用）
    try:
        settings = get_settings()
        level = log_level or settings.LOG_LEVEL
        log_file_name = log_file or settings.LOG_FILE
    except (SettingsValidationError, OSError, IOError):
        # 設定が読み込めない場合やファイルI/Oエラーの場合はデフォルト値を使用
        # - SettingsValidationError: 環境変数が不足している場合
        # - OSError/IOError: .envファイルの読み込みエラー
        level = log_level or "INFO"
        log_file_name = log_file or "app.log"

    # ログレベルの決定
    log_level_num = getattr(logging, level.upper(), logging.INFO)

    # ロガー取得
    logger = logging.getLogger(name)
    logger.setLevel(log_level_num)

    # 既存のハンドラをクリア（重複登録防止）
    logger.handlers.clear()

    # フォーマッタ作成
    formatter = StructuredFormatter(use_json=use_json)

    # コンソールハンドラの追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level_num)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラの追加
    if log_file_name:
        # ログディレクトリの作成
        if log_dir:
            log_path = Path(log_dir) / log_file_name
        else:
            log_path = Path("logs") / log_file_name

        log_path.parent.mkdir(parents=True, exist_ok=True)

        # ローテーションファイルハンドラ
        file_handler = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level_num)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # 親ロガーへの伝播を無効化（重複出力防止）
    logger.propagate = False

    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """ロガーを取得（シンプルなインターフェース）

    Args:
        name: ロガー名

    Returns:
        ロガー
    """
    return setup_logger(name)


def get_default_logger() -> logging.Logger:
    """デフォルトロガーを取得

    Returns:
        デフォルトロガー
    """
    return _DefaultLogger.get()


# =============================================================================
# リクエストID管理関数
# =============================================================================


def set_request_id(request_id: str) -> None:
    """リクエストIDを設定

    Args:
        request_id: リクエストID
    """
    request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """リクエストIDを取得

    Returns:
        リクエストID（未設定の場合はNone）
    """
    return request_id_var.get()


def clear_request_id() -> None:
    """リクエストIDをクリア"""
    request_id_var.set(None)
