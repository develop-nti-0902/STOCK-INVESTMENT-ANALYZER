"""スキーマ基底ページネーションの単体テスト.

実装は以前 `test_base_schema.py` にあった内容をこのファイルに移動しました。
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.core.base import BaseSchema, PaginationRequestSchema, PaginationResponseSchema


def test_base_schema_serializes_datetimes_to_iso():
    """BaseSchema の日時シリアライズが ISO 形式であることを検証する."""
    now = datetime.now(timezone.utc)
    s = BaseSchema(id=1, created_at=now, updated_at=now)
    json_dump = s.model_dump_json()
    assert now.isoformat() in json_dump


def test_pagination_request_defaults_and_validators():
    """PaginationRequestSchema のデフォルト値とバリデーションを確認する."""
    p = PaginationRequestSchema()
    assert p.limit == 100
    assert p.offset == 0

    with pytest.raises(ValidationError):
        PaginationRequestSchema(limit=1001)

    with pytest.raises(ValidationError):
        PaginationRequestSchema(limit=0)


def test_pagination_response_requires_non_negative_total():
    """PaginationResponseSchema が非負の total を要求することを検証する."""
    r = PaginationResponseSchema(total=0, limit=10, offset=0)
    assert r.total == 0

    with pytest.raises(ValidationError):
        PaginationResponseSchema(total=-1, limit=10, offset=0)
