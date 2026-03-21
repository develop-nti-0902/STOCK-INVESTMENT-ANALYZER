"""Unit tests for `app.schemas.relative_strength` schemas."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.relative_strength import (
    CalculateRelativeStrengthRequest,
    RelativeStrengthDateResponse,
    RelativeStrengthAllResponse,
)


def test_calculate_relative_strength_request_valid():
    """CalculateRelativeStrengthRequest が有効なデータで作成されることを検証する."""
    req = CalculateRelativeStrengthRequest(target_date=date(2024, 1, 15))

    assert req.target_date == date(2024, 1, 15)


def test_calculate_relative_strength_request_string_date_parsing():
    """CalculateRelativeStrengthRequest が文字列日付をパースすることを検証する."""
    req = CalculateRelativeStrengthRequest(target_date="2024-01-15")

    assert req.target_date == date(2024, 1, 15)


def test_calculate_relative_strength_request_invalid_date_format():
    """CalculateRelativeStrengthRequest が不正な日付形式で例外を発生させることを検証する."""
    with pytest.raises(ValidationError):
        CalculateRelativeStrengthRequest(target_date="invalid-date")


def test_calculate_relative_strength_request_forbids_extra_fields():
    """CalculateRelativeStrengthRequest が追加フィールドを拒否することを検証する."""
    with pytest.raises(ValidationError):
        CalculateRelativeStrengthRequest(target_date=date(2024, 1, 15), extra_field="value")


def test_relative_strength_date_response_valid():
    """RelativeStrengthDateResponse が有効なデータで作成されることを検証する."""
    resp = RelativeStrengthDateResponse(
        status="completed",
        calculation_date="2024-01-15",
        rowcount=10,
        skipped_count=2,
        error_count=0,
        message="Success",
    )

    assert resp.status == "completed"
    assert resp.calculation_date == "2024-01-15"
    assert resp.rowcount == 10
    assert resp.skipped_count == 2
    assert resp.error_count == 0
    assert resp.message == "Success"


def test_relative_strength_date_response_allows_extra_fields():
    """RelativeStrengthDateResponse が追加フィールドを許可することを検証する."""
    resp = RelativeStrengthDateResponse(
        status="completed",
        calculation_date="2024-01-15",
        rowcount=10,
        skipped_count=2,
        error_count=0,
        extra_field="allowed",
    )

    assert resp.status == "completed"
    assert hasattr(resp, "extra_field")


def test_relative_strength_date_response_partial_error_status():
    """RelativeStrengthDateResponse の partial_error ステータスを検証する."""
    resp = RelativeStrengthDateResponse(
        status="partial_error",
        calculation_date="2024-01-15",
        rowcount=8,
        skipped_count=2,
        error_count=2,
    )

    assert resp.status == "partial_error"
    assert resp.error_count == 2


def test_relative_strength_all_response_valid():
    """RelativeStrengthAllResponse が有効なデータで作成されることを検証する."""
    resp = RelativeStrengthAllResponse(
        status="completed",
        total_symbols=100,
        total_rowcount=1000,
        error_count=0,
        message="Success",
    )

    assert resp.status == "completed"
    assert resp.total_symbols == 100
    assert resp.total_rowcount == 1000
    assert resp.error_count == 0
    assert resp.message == "Success"


def test_relative_strength_all_response_missing_required_field():
    """RelativeStrengthAllResponse が必須フィールド不足で例外を発生させることを検証する."""
    with pytest.raises(ValidationError):
        RelativeStrengthAllResponse(
            status="completed",
            total_symbols=100,
            # missing total_rowcount
            error_count=0,
        )


def test_relative_strength_all_response_partial_error_status():
    """RelativeStrengthAllResponse の partial_error ステータスを検証する."""
    resp = RelativeStrengthAllResponse(
        status="partial_error",
        total_symbols=100,
        total_rowcount=900,
        error_count=5,
    )

    assert resp.status == "partial_error"
    assert resp.error_count == 5


def test_relative_strength_date_response_status_enum_options():
    """RelativeStrengthDateResponse が複数ステータスタイプをサポートすることを検証する."""
    for status in ["completed", "partial_error", "no_data"]:
        resp = RelativeStrengthDateResponse(
            status=status,
            calculation_date="2024-01-15",
            rowcount=0,
            skipped_count=0,
            error_count=0,
        )
        assert resp.status == status
