"""
例外処理モジュール - データベース関連例外

データベース操作に関連する例外クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3.3章
"""

from typing import Optional

from app.exceptions.base import AppException


class DatabaseError(AppException):
    """データベース操作の基底例外クラス"""

    def __init__(
        self,
        *,
        message: str = "Database operation failed",
        error_code: str = "DB_ERROR",
        status_code: int = 500,
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            context=context,
        )


class StockDataError(DatabaseError):
    """株価データ操作に関するエラー"""

    def __init__(
        self,
        *,
        message: str = "Stock data operation failed",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="STOCK_DATA_ERROR",
            status_code=500,
            context=context,
        )


class MasterDataError(DatabaseError):
    """銘柄マスタデータ操作に関するエラー"""

    def __init__(
        self,
        *,
        message: str = "Master data operation failed",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="MASTER_DATA_ERROR",
            status_code=500,
            context=context,
        )


class ConstraintViolationError(DatabaseError):
    """データベース制約違反エラー"""

    def __init__(
        self,
        *,
        message: str = "Database constraint violation",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="CONSTRAINT_VIOLATION",
            status_code=400,
            context=context,
        )


class DuplicateRecordError(ConstraintViolationError):
    """レコード重複エラー（UNIQUE制約違反）"""

    def __init__(
        self,
        *,
        message: str = "Duplicate record detected",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            context=context,
        )
        self.error_code = "DUPLICATE_RECORD"
        self.status_code = 409


class RecordNotFoundError(DatabaseError):
    """レコード未検出エラー"""

    def __init__(
        self,
        *,
        message: str = "Record not found",
        context: Optional[dict] = None,
    ):
        super().__init__(
            message=message,
            error_code="RECORD_NOT_FOUND",
            status_code=404,
            context=context,
        )
