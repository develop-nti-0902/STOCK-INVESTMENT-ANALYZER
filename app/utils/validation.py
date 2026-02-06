"""入力検証ユーティリティ.

リポジトリやサービス層で利用されるページネーションや上限チェックの
共通ヘルパーを提供します。

ノート:
    - ``validate_pagination`` を使って ``skip`` と ``limit`` の検証を行ってください。
"""

from __future__ import annotations

from typing import Optional

from app.exceptions.validation import FieldValidationError
from app.utils.config import get_settings


def validate_pagination(skip: Optional[int], limit: int) -> None:
    """skip と limit の基本検証を行うヘルパー.

    - `skip` は 0 以上であること
    - `limit` は正の値で、設定上限を超えないこと

    Args:
        skip: オフセット（None の場合は検証しない）
        limit: 取得上限

    Raises:
        FieldValidationError: 引数検証に失敗した場合
    """
    if skip is not None and skip < 0:
        raise FieldValidationError(message="skip must be >= 0")
    if limit <= 0:
        raise FieldValidationError(message="limit must be positive")
    settings = get_settings()
    max_limit = settings.MAX_RECENT_LIMIT
    if limit > max_limit:
        raise FieldValidationError(message=f"limit too large; max={max_limit}")


__all__ = ["validate_pagination"]
