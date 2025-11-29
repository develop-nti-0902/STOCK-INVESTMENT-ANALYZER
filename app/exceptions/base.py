"""
例外処理モジュール - 基底クラス

全てのカスタム例外の基底クラスを定義する。
仕様書: docs/architecture/layers/common_modules.md 3章
"""

from typing import Optional

from fastapi import HTTPException


class AppException(Exception):
    """
    アプリケーション全体の基底例外クラス

    全てのカスタム例外はこのクラスを継承する。
    HTTPステータスコード、エラーコード、詳細情報を保持し、
    FastAPI HTTPExceptionへの変換メソッドを提供する。
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[dict] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Args:
            message: エラーメッセージ
            error_code: エラーコード（例: "DB_ERROR"）
            status_code: HTTPステータスコード（デフォルト: 500）
            details: エラー詳細情報（オプション）
            original_error: 元の例外オブジェクト（オプション）
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.original_error = original_error

    def to_dict(self) -> dict:
        """
        例外を辞書形式に変換（APIレスポンス用）

        Returns:
            dict: エラーレスポンス形式の辞書
        """
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def to_http_exception(self) -> HTTPException:
        """
        FastAPI HTTPExceptionに変換

        Returns:
            HTTPException: FastAPI用の例外オブジェクト
        """
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict(),
        )

    def __str__(self) -> str:
        """文字列表現"""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """デバッグ用表現"""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"status_code={self.status_code}, "
            f"details={self.details!r})"
        )
