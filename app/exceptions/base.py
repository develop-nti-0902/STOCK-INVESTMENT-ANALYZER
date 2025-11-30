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

    各サブクラスはクラス属性でデフォルトのメッセージ、エラーコード、
    ステータスコードを定義できます。コンストラクタはそれらを上書き可能
    な引数を受け取り、共通の初期化処理を行います。
    """

    # サブクラスで上書きして使うデフォルト値
    default_message: str = "Application error"
    default_error_code: str = "APP_ERROR"
    default_status_code: int = 500

    def __init__(
        self,
        *,
        message: Optional[str] = None,
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[dict] = None,
    ):
        """共通初期化処理

        Args:
            message: オーバーライドするメッセージ（未指定時はクラス属性を使用）
            error_code: オーバーライドするエラーコード（未指定時はクラス属性を使用）
            status_code: オーバーライドする HTTP ステータスコード
            context: 任意のコンテキスト辞書
        """
        # クラス属性をデフォルトとして使用し、引数で上書き可能にする
        resolved_message = (
            message
            if message is not None
            else getattr(self, "default_message", "Application error")
        )
        resolved_error_code = (
            error_code
            if error_code is not None
            else getattr(self, "default_error_code", "APP_ERROR")
        )
        resolved_status = (
            status_code
            if status_code is not None
            else getattr(self, "default_status_code", 500)
        )

        super().__init__(resolved_message)
        self.message = resolved_message
        self.error_code = resolved_error_code
        self.status_code = resolved_status
        ctx = context or {}
        self.details = ctx.get("details", {})
        self.original_error = ctx.get("original_error")

    def to_dict(self) -> dict:
        """例外を辞書形式に変換（APIレスポンス用）"""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }

    def to_http_exception(self) -> HTTPException:
        """FastAPI HTTPExceptionに変換"""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict(),
        )

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"status_code={self.status_code}, "
            f"details={self.details!r})"
        )
