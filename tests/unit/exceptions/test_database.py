"""
例外処理モジュールのテスト - データベース関連例外
"""

from app.exceptions.base import AppException

# pylint: disable=too-few-public-methods
from app.exceptions.database import (
    ConstraintViolationError,
    DatabaseError,
    DuplicateRecordError,
    MasterDataError,
    RecordNotFoundError,
    StockDataError,
)


class TestDatabaseError:
    """DatabaseError基底クラスのテスト"""

    def test_default_initialization(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でDatabaseErrorを初期化
        exc = DatabaseError()

        # Assert: デフォルト値が正しく設定されていることを確認
        assert exc.message == "Database operation failed"
        assert exc.error_code == "DB_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, AppException)

    def test_custom_message(self):
        """
        カスタムメッセージでの初期化
        """
        # Arrange: (特になし)

        # Act: カスタムメッセージでDatabaseErrorを初期化
        exc = DatabaseError(message="Custom DB error")

        # Assert: カスタムメッセージが設定されていることを確認
        assert exc.message == "Custom DB error"
        assert exc.error_code == "DB_ERROR"


class TestStockDataError:
    """StockDataErrorのテスト"""

    def test_default_initialization(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でStockDataErrorを初期化
        exc = StockDataError()

        # Assert: デフォルト値が正しく設定され、DatabaseErrorを継承していることを確認
        assert exc.message == "Stock data operation failed"
        assert exc.error_code == "STOCK_DATA_ERROR"
        assert exc.status_code == 500
        assert isinstance(exc, DatabaseError)

    def test_with_details(self):
        """
        詳細情報を含む初期化
        """
        # Arrange: (特になし)

        # Act: 詳細情報を含めてStockDataErrorを初期化
        exc = StockDataError(
            message="Failed to insert stock data",
            context={"details": {"symbol": "7203.T", "table": "stocks_daily"}},
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Failed to insert stock data"
        assert exc.details["symbol"] == "7203.T"

    def helper_noop(self):
        """pylint対応用の補助メソッド（テスト動作には影響なし）。"""
        return None


class TestMasterDataError:
    """MasterDataErrorのテスト"""

    def test_default_initialization(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でMasterDataErrorを初期化
        exc = MasterDataError()

        # Assert: デフォルト値が正しく設定されていることを確認
        assert exc.message == "Master data operation failed"
        assert exc.error_code == "MASTER_DATA_ERROR"
        assert exc.status_code == 500

    def helper_noop(self):
        """pylint対応用の補助メソッド（テスト動作には影響なし）。"""
        return None


class TestConstraintViolationError:
    """ConstraintViolationErrorのテスト"""

    def test_default_initialization(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でConstraintViolationErrorを初期化
        exc = ConstraintViolationError()

        # Assert: デフォルト値が正しく設定され、DatabaseErrorを継承していることを確認
        assert exc.message == "Database constraint violation"
        assert exc.error_code == "CONSTRAINT_VIOLATION"
        assert exc.status_code == 400
        assert isinstance(exc, DatabaseError)

    def helper_noop(self):
        """pylint対応用の補助メソッド（テスト動作には影響なし）。"""
        return None


class TestDuplicateRecordError:
    """DuplicateRecordErrorのテスト"""

    def test_default_initialization(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でDuplicateRecordErrorを初期化
        exc = DuplicateRecordError()

        # Assert: デフォルト値が正しく設定され、ConstraintViolationErrorを継承していることを確認
        assert exc.message == "Duplicate record detected"
        assert exc.error_code == "DUPLICATE_RECORD"
        assert exc.status_code == 409
        assert isinstance(exc, ConstraintViolationError)

    def test_with_details(self):
        """
        詳細情報を含む初期化
        """
        # Arrange: (特になし)

        # Act: 詳細情報を含めてDuplicateRecordErrorを初期化
        exc = DuplicateRecordError(
            message="Duplicate stock data",
            context={
                "details": {
                    "symbol": "7203.T",
                    "date": "2025-11-29",
                    "constraint": "unique_symbol_date",
                }
            },
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Duplicate stock data"
        assert exc.details["symbol"] == "7203.T"

    def helper_noop(self):
        """pylint対応用の補助メソッド（テスト動作には影響なし）。"""
        return None


class TestRecordNotFoundError:
    """RecordNotFoundErrorのテスト"""

    def test_default_initialization(self):
        """
        デフォルト値での初期化
        """
        # Arrange: (特になし)

        # Act: デフォルト値でRecordNotFoundErrorを初期化
        exc = RecordNotFoundError()

        # Assert: デフォルト値が正しく設定され、DatabaseErrorを継承していることを確認
        assert exc.message == "Record not found"
        assert exc.error_code == "RECORD_NOT_FOUND"
        assert exc.status_code == 404
        assert isinstance(exc, DatabaseError)

    def test_with_details(self):
        """
        詳細情報を含む初期化
        """
        # Arrange: (特になし)

        # Act: 詳細情報を含めてRecordNotFoundErrorを初期化
        exc = RecordNotFoundError(
            message="Stock not found",
            context={"details": {"symbol": "9999.T"}},
        )

        # Assert: メッセージと詳細情報が正しく設定されていることを確認
        assert exc.message == "Stock not found"
        assert exc.details["symbol"] == "9999.T"
