"""ロガーモジュールの単体テスト.

ロガーモジュールの機能をテストします。
- ログレベル
- ファイル出力
- コンソール出力
- ログローテーション
- リクエストIDの付与
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import pytest

from app.utils.logger import (
    StructuredFormatter,
    clear_request_id,
    get_logger,
    get_request_id,
    set_request_id,
    setup_logger,
)


@pytest.fixture(autouse=True)
def cleanup_logging():
    """各テスト後にロガーのハンドラと request_id をクリーンアップする."""
    yield
    # リクエストID をクリア
    try:
        clear_request_id()
    except (RuntimeError, ValueError):
        # ContextVarの操作エラーを無視
        pass

    # 全ての Logger のハンドラを閉じて削除（テスト間の干渉を防止）
    for _name, logger_obj in list(logging.Logger.manager.loggerDict.items()):
        if isinstance(logger_obj, logging.Logger):
            for handler in getattr(logger_obj, "handlers", [])[:]:
                try:
                    handler.close()
                except (OSError, ValueError, RuntimeError):
                    # ファイルハンドラのクローズエラーを無視
                    pass
                try:
                    logger_obj.removeHandler(handler)
                except (ValueError, RuntimeError):
                    # ハンドラの削除エラーを無視
                    pass
            try:
                logger_obj.setLevel(logging.NOTSET)
                logger_obj.propagate = True
            except (ValueError, RuntimeError):
                # ロガー設定のリセットエラーを無視
                pass


class TestStructuredFormatter:
    """StructuredFormatterのテスト."""

    def test_format_text_without_request_id(self) -> None:
        """リクエストIDなしのテキスト形式ログフォーマット."""
        # Arrange
        formatter = StructuredFormatter(use_json=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        formatted = formatter.format(record)

        # Assert
        assert "[INFO]" in formatted
        assert "[test]" in formatted
        assert "Test message" in formatted

    def test_format_text_with_request_id(self) -> None:
        """リクエストID付きのテキスト形式ログフォーマット."""
        # Arrange
        set_request_id("req-123456")
        formatter = StructuredFormatter(use_json=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        formatted = formatter.format(record)

        # Assert
        assert "[INFO]" in formatted
        assert "[req-123456]" in formatted
        assert "[test]" in formatted
        assert "Test message" in formatted

        # Cleanup
        clear_request_id()

    def test_format_json_without_request_id(self) -> None:
        """リクエストIDなしのJSON形式ログフォーマット."""
        # Arrange
        formatter = StructuredFormatter(use_json=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Assert
        assert log_data["level"] == "INFO"
        assert log_data["module"] == "test"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data
        assert "request_id" not in log_data

    def test_format_json_with_request_id(self) -> None:
        """リクエストID付きのJSON形式ログフォーマット."""
        # Arrange
        set_request_id("req-789012")
        formatter = StructuredFormatter(use_json=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Act
        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Assert
        assert log_data["level"] == "INFO"
        assert log_data["module"] == "test"
        assert log_data["message"] == "Test message"
        assert log_data["request_id"] == "req-789012"
        assert "timestamp" in log_data

        # Cleanup
        clear_request_id()


class TestSetupLogger:
    """setup_logger関数のテスト."""

    def test_setup_logger_default(self) -> None:
        """デフォルト設定でロガーをセットアップ."""
        # Arrange / Act
        logger = setup_logger(name="test_default")

        # Assert
        assert logger.name == "test_default"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logger_with_log_level(self) -> None:
        """ログレベルを指定してロガーをセットアップ."""
        # Arrange / Act
        logger = setup_logger(name="test_level", log_level="DEBUG")

        # Assert
        assert logger.level == logging.DEBUG

    def test_setup_logger_with_file_output(self) -> None:
        """ファイル出力を指定してロガーをセットアップ."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = "test.log"
            # Arrange
            logger = setup_logger(
                name="test_file",
                log_file=log_file,
                log_dir=temp_dir,
            )

            # Act: ログ出力
            logger.info("Test log message")

            # ハンドラをクローズ
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

            # Assert: ファイルが作成され、内容が含まれること
            log_path = Path(temp_dir) / log_file
            assert log_path.exists()
            content = log_path.read_text(encoding="utf-8")
            assert "Test log message" in content

    def test_setup_logger_with_json_format(self) -> None:
        """JSON形式でロガーをセットアップ."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = "test_json.log"
            # Arrange
            logger = setup_logger(
                name="test_json",
                log_file=log_file,
                log_dir=temp_dir,
                use_json=True,
            )

            # Act: ログ出力
            logger.info("Test JSON log")

            # ハンドラをクローズ
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

            # Assert: ファイル内容がJSONで期待のフィールドを持つこと
            log_path = Path(temp_dir) / log_file
            content = log_path.read_text(encoding="utf-8")
            log_data = json.loads(content.strip())
            assert log_data["message"] == "Test JSON log"
            assert log_data["level"] == "INFO"


class TestGetLogger:  # pylint: disable=too-few-public-methods
    """get_logger関数のテスト."""

    def test_get_logger(self) -> None:
        """get_logger関数でロガーを取得."""
        # Arrange / Act
        logger = get_logger("test_get_logger")

        # Assert
        assert logger.name == "test_get_logger"
        assert isinstance(logger, logging.Logger)


class TestRequestIdManagement:
    """リクエストID管理機能のテスト."""

    def test_set_and_get_request_id(self) -> None:
        """リクエストIDの設定と取得."""
        # Arrange
        test_id = "req-test-123"

        # Act
        set_request_id(test_id)

        # Assert
        assert get_request_id() == test_id

        # Cleanup
        clear_request_id()

    def test_clear_request_id(self) -> None:
        """リクエストIDのクリア."""
        # Arrange
        set_request_id("req-test-456")

        # Act
        clear_request_id()

        # Assert
        assert get_request_id() is None

    def test_get_request_id_when_not_set(self) -> None:
        """リクエストID未設定時の取得."""
        # Arrange / Act
        clear_request_id()

        # Assert
        assert get_request_id() is None


class TestLogRotation:
    """ログローテーション機能のテスト."""

    def test_log_rotation(self) -> None:
        """ログローテーションの動作確認."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = "test_rotation.log"
            # 小さいサイズでログローテーションを設定
            logger = setup_logger(
                name="test_rotation",
                log_file=log_file,
                log_dir=temp_dir,
                max_bytes=100,  # 100バイト
                backup_count=2,
            )
            # Arrange / Act: ログを大量に出力してローテーションをトリガー
            for i in range(50):
                logger.info("Test log message number %d", i)

            # ハンドラをクローズ
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

            # Assert: ログファイルとバックアップファイルが存在することを確認
            log_path = Path(temp_dir) / log_file
            assert log_path.exists()
            backup_files = list(Path(temp_dir).glob(f"{log_file}.*"))
            assert len(backup_files) > 0


class TestLogLevels:
    """各ログレベルのテスト."""

    def test_debug_level(self) -> None:
        """DEBUGレベルのログ."""
        # Arrange / Act
        logger = setup_logger(name="test_debug", log_level="DEBUG")
        logger.debug("Debug message")

        # Assert
        assert logger.level == logging.DEBUG

    def test_info_level(self) -> None:
        """INFOレベルのログ."""
        # Arrange / Act
        logger = setup_logger(name="test_info", log_level="INFO")
        logger.info("Info message")

        # Assert
        assert logger.level == logging.INFO

    def test_warning_level(self) -> None:
        """WARNINGレベルのログ."""
        # Arrange / Act
        logger = setup_logger(name="test_warning", log_level="WARNING")
        logger.warning("Warning message")

        # Assert
        assert logger.level == logging.WARNING

    def test_error_level(self) -> None:
        """ERRORレベルのログ."""
        # Arrange / Act
        logger = setup_logger(name="test_error", log_level="ERROR")
        logger.error("Error message")

        # Assert
        assert logger.level == logging.ERROR

    def test_critical_level(self) -> None:
        """CRITICALレベルのログ."""
        # Arrange / Act
        logger = setup_logger(name="test_critical", log_level="CRITICAL")
        logger.critical("Critical message")

        # Assert
        assert logger.level == logging.CRITICAL
