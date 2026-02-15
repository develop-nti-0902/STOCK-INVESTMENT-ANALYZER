"""スキーマ基底ページネーションの単体テスト."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.base import BaseSchema, PaginationRequestSchema, PaginationResponseSchema


def test_base_schema_serializes_datetimes_to_iso():
    """日時がISO形式にシリアライズされることを検証します."""
    now = datetime.now(timezone.utc)
    s = BaseSchema(id=1, created_at=now, updated_at=now)
    json_dump = s.model_dump_json()
    assert now.isoformat() in json_dump


def test_pagination_request_defaults_and_validators():
    """PaginationRequestSchema のデフォルトとバリデータを検証します."""
    p = PaginationRequestSchema()
    assert p.limit == 100
    assert p.offset == 0

    # invalid limit (too large)
    with pytest.raises(ValidationError):
        PaginationRequestSchema(limit=1001)

    with pytest.raises(ValidationError):
        PaginationRequestSchema(limit=0)


def test_pagination_response_requires_non_negative_total():
    """PaginationResponseSchema が非負の total を要求することを検証します."""
    r = PaginationResponseSchema(total=0, limit=10, offset=0)
    assert r.total == 0

    with pytest.raises(ValidationError):
        PaginationResponseSchema(total=-1, limit=10, offset=0)
