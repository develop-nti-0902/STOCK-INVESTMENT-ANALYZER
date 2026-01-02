"""例外処理モジュール - データベース関連例外.

データベース操作に関連する例外クラスを定義します。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from app.exceptions.base import AppException


class DatabaseError(AppException):
    """データベース操作の基底例外クラス.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Database operation failed"
    default_error_code = "DB_ERROR"
    default_status_code = 500


class StockDataError(DatabaseError):
    """株価データ操作に関するエラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Stock data operation failed"
    default_error_code = "STOCK_DATA_ERROR"
    default_status_code = 500


class MasterDataError(DatabaseError):
    """銘柄マスタデータ操作に関するエラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Master data operation failed"
    default_error_code = "MASTER_DATA_ERROR"
    default_status_code = 500


class ConstraintViolationError(DatabaseError):
    """データベース制約違反エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Database constraint violation"
    default_error_code = "CONSTRAINT_VIOLATION"
    default_status_code = 400


class DuplicateRecordError(ConstraintViolationError):
    """レコード重複エラー（UNIQUE制約違反）.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Duplicate record detected"
    default_error_code = "DUPLICATE_RECORD"
    default_status_code = 409


class RecordNotFoundError(DatabaseError):
    """レコード未検出エラー.

    Attributes:
        default_message (str): デフォルトメッセージ
        default_error_code (str): デフォルトエラーコード
        default_status_code (int): デフォルトHTTPステータスコード
    """

    default_message = "Record not found"
    default_error_code = "RECORD_NOT_FOUND"
    default_status_code = 404
