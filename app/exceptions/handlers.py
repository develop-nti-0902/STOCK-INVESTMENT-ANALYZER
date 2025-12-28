"""
例外処理モジュール - FastAPI例外ハンドラ

FastAPIアプリケーション全体の例外処理を統一する。
仕様書: docs/architecture/layers/common_modules.md 3.4章
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.base import AppException

logger = logging.getLogger(__name__)


def generate_request_id() -> str:
    """
    リクエストIDを生成する

    Returns:
        str: タイムスタンプベースのリクエストID
    """
    return f"req-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


def create_error_response(
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    統一されたエラーレスポンス形式を生成する

    Args:
        error_code: エラーコード
        message: エラーメッセージ
        details: エラー詳細情報（オプション）
        request_id: リクエストID（オプション）

    Returns:
        dict: エラーレスポンス形式の辞書
    """
    return {
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
        },
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id or generate_request_id(),
        },
    }


async def app_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    AppException(カスタム例外)のハンドラ

    Args:
        request: FastAPIリクエストオブジェクト
        exc: カスタム例外オブジェクト

    Returns:
        JSONResponse: 統一フォーマットのエラーレスポンス
    """
    request_id = generate_request_id()

    # 型チェック
    if not isinstance(exc, AppException):
        # 本ハンドラはAppException専用。異なる型の場合は一般ハンドラ相当で応答
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(
                error_code="INTERNAL_SERVER_ERROR",
                message=str(exc) or "Unexpected exception",
            ),
        )

    # ログ出力
    logger.error(
        "[%s] AppException occurred: %s - %s",
        request_id,
        exc.error_code,
        exc.message,
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # 元の例外がある場合はログに記録
    if exc.original_error:
        logger.error(
            "[%s] Original exception: %s",
            request_id,
            type(exc.original_error).__name__,
            exc_info=exc.original_error,
        )

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        ),
    )


async def http_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    FastAPI標準HTTPExceptionのハンドラ

    Args:
        request: FastAPIリクエストオブジェクト
        exc: HTTPException例外オブジェクト

    Returns:
        JSONResponse: 統一フォーマットのエラーレスポンス
    """
    request_id = generate_request_id()

    # 型チェック
    if not isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=create_error_response(
                error_code="INTERNAL_SERVER_ERROR",
                message=str(exc) or "Unexpected exception",
            ),
        )

    # ログ出力
    logger.warning(
        "[%s] HTTPException occurred: %s - %s",
        request_id,
        exc.status_code,
        exc.detail,
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # exc.detailが既に辞書形式の場合はそれを使用、そうでなければ文字列として扱う
    details: dict[str, Any]
    if isinstance(exc.detail, dict):
        # ネストされた `error` オブジェクト形式をサポート
        if isinstance(exc.detail.get("error"), dict):
            error_obj = exc.detail.get("error", {})
            error_code = error_obj.get("code", "HTTP_ERROR")
            message = error_obj.get("message", str(error_obj))
            details = error_obj.get("details", {})  # type: ignore[assignment]
        else:
            # 旧来のフラット形式をサポート
            error_code = exc.detail.get("error", "HTTP_ERROR")
            message = exc.detail.get("message", str(exc.detail))
            details = exc.detail.get("details", {})  # type: ignore[assignment]
    else:
        error_code = "HTTP_ERROR"
        message = str(exc.detail)
        details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=error_code,
            message=message,
            details=details,
            request_id=request_id,
        ),
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Pydantic RequestValidationErrorのハンドラ

    Args:
        request: FastAPIリクエストオブジェクト
        exc: RequestValidationError例外オブジェクト

    Returns:
        JSONResponse: 統一フォーマットのエラーレスポンス
    """
    # 型チェック
    if not isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=create_error_response(
                error_code="BAD_REQUEST",
                message=str(exc) or "Bad request",
            ),
        )

    request_id = generate_request_id()

    # バリデーションエラーの詳細を整形
    validation_errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        validation_errors.append(
            {
                "field": field,
                "message": error["msg"],
                "type": error["type"],
                "input": error.get("input"),
            }
        )

    # ログ出力
    logger.warning(
        "[%s] Validation error occurred",
        request_id,
        extra={
            "validation_errors": validation_errors,
            "path": request.url.path,
            "method": request.method,
        },
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=create_error_response(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"validation_errors": validation_errors},
            request_id=request_id,
        ),
    )


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    予期しない例外の汎用ハンドラ

    Args:
        request: FastAPIリクエストオブジェクト
        exc: 例外オブジェクト

    Returns:
        JSONResponse: 統一フォーマットのエラーレスポンス
    """
    request_id = generate_request_id()

    # 詳細なエラーログを出力
    logger.critical(
        "[%s] Unexpected exception occurred: %s - %s",
        request_id,
        type(exc).__name__,
        str(exc),
        extra={
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
        exc_info=True,
    )

    # 本番環境では詳細なエラー情報を隠す。DEBUGはアプリ状態から参照
    debug_mode = False
    # getattrを用いて安全に属性参照（例外を投げない）
    app_obj = getattr(request, "app", None)
    app_state = getattr(app_obj, "state", None)
    settings = getattr(app_state, "settings", None) if app_state else None
    debug_mode = bool(getattr(settings, "DEBUG", False))

    response_details: dict[str, Any] = {"exception_type": type(exc).__name__}
    if debug_mode:
        response_details["traceback"] = traceback.format_exc()

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error_code="INTERNAL_SERVER_ERROR",
            message=(
                "An unexpected error occurred"
                if not debug_mode
                else str(exc) or "Unexpected exception"
            ),
            details=response_details,
            request_id=request_id,
        ),
    )
