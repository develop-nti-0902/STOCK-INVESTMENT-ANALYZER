"""Unit tests for validation utilities."""

import pytest

from app.exceptions.validation import FieldValidationError
from app.utils.validation import validate_pagination


def test_validate_pagination_ok():
    """skip=0, limit=1 の正しい組合せが受け入れられることを検証する."""
    validate_pagination(0, 1)


def test_validate_pagination_negative_skip():
    """負の skip 値が FieldValidationError を引き起こすことを確認する."""
    with pytest.raises(FieldValidationError):
        validate_pagination(-1, 10)


def test_validate_pagination_limit_zero():
    """limit=0 が FieldValidationError を発生させることを確認する."""
    with pytest.raises(FieldValidationError):
        validate_pagination(0, 0)
