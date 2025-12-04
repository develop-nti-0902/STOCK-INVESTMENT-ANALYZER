"""
エラーハンドリングデコレータ

サービス層の共通エラーハンドリングを提供します。
仕様書: docs/architecture/layers/service_layer.md 6.1章
"""

import functools
import inspect
from typing import Any, Callable

from app.exceptions import ServiceError

# モジュール全体で広義の Exception 捕捉、TODO 指摘、重複コード検出を抑止
# （設計上サービス境界での全例外ラップを意図しているため）
# pylint: disable=broad-exception-caught, fixme, duplicate-code


def handle_service_error(
    error_message: str = "Service operation failed",
    error_code: str = "SERVICE_ERROR",
    reraise: bool = True,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    サービス層のエラーを統一的にハンドリングするデコレータ

    Args:
        error_message: エラーメッセージ（デフォルト: "Service operation failed"）
        error_code: エラーコード（デフォルト: "SERVICE_ERROR"）
        reraise: 例外を再送出するかどうか（デフォルト: True）

    Returns:
        Callable: デコレータ関数

    Examples:
        >>> @handle_service_error(error_message="Failed to fetch stock data")
        ... async def fetch_stock_data(symbol: str) -> StockData:
        ...     # データ取得処理
        ...     return stock_data

    Note:
        - 非同期関数と同期関数の両方に対応
        - reraise=Falseの場合、エラーログのみ記録してNoneを返す
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except ServiceError:
                # ServiceErrorはそのまま再送出
                raise
            except Exception as e:  # NOSONAR - wrap into ServiceError
                # ロガー統合時にログ出力を追加予定
                # 補足: ここではサービス層の境界で発生した「予期しない例外」を
                # ServiceError にラップして上位に伝搬する設計を採用しているため、
                # 静的解析ツールの「Catching too general exception Exception」を
                # 意図的に抑制しています。
                # その他の例外はServiceErrorでラップ
                service_error = ServiceError(
                    message=f"{error_message}: {str(e)}",
                    error_code=error_code,
                    context={
                        "original_error": type(e).__name__,
                        "args": args,
                        "kwargs": kwargs,
                    },
                )
                if reraise:
                    raise service_error from e
                # TODO: エラーログ出力を追加（後で実装）
                return None  # type: ignore

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except ServiceError:
                # ServiceErrorはそのまま再送出
                raise
            except Exception as e:  # NOSONAR - wrap into ServiceError
                # ロガー統合時にログ出力を追加予定
                # 補足: ここではサービス層の境界で発生した「予期しない例外」を
                # ServiceError にラップして上位に伝搬する設計を採用しているため、
                # 静的解析ツールの「Catching too general exception Exception」を
                # 意図的に抑制しています。
                service_error = ServiceError(
                    message=f"{error_message}: {str(e)}",
                    error_code=error_code,
                    context={
                        "original_error": type(e).__name__,
                        "args": args,
                        "kwargs": kwargs,
                    },
                )
                if reraise:
                    raise service_error from e
                # TODO: エラーログ出力を追加（後で実装）
                return None  # type: ignore

        # 関数が非同期かどうかで切り替え
        return (
            async_wrapper
            if inspect.iscoroutinefunction(func)
            else sync_wrapper
        )  # type: ignore

    return decorator
