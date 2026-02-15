"""EDINET 財務諸表スキーマのバリデーション単体テスト."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.market_data.edinet import EdinetBalanceSheetCreate, EdinetBalanceSheetLatest


def sample_payload():
    """サンプルの有効なペイロードを返します."""
    return {
        "doc_id": " DOC123 ",
        "sec_code": "7203",
        "filer_name": " Example Corp ",
        "submission_date": date(2025, 1, 31),
        "period_end_date": date(2024, 12, 31),
        "fiscal_year": 2024,
        "report_type": "annual",
        "total_assets": "123456.78",
        "current_assets": 1000,
        "non_current_assets": None,
        "cash_and_equivalents": "12.34",
        "total_liabilities": "50000",
        "current_liabilities": None,
        "non_current_liabilities": None,
        "total_equity": "73456.78",
        "shareholders_equity": "70000",
        "retained_earnings": "3456.78",
        "candidate_contexts": "CTX1",
        "candidate_keys": "KEY1",
        "is_consolidated": True,
    }


def test_create_valid_payload_converts_and_strips():
    """有効なペイロードが変換・トリムされることを検証します."""
    payload = sample_payload()
    obj = EdinetBalanceSheetCreate(**payload)

    # strings are stripped
    assert obj.doc_id == "DOC123"
    assert obj.filer_name == "Example Corp"

    # numeric fields converted to Decimal
    assert isinstance(obj.total_assets, Decimal)
    assert obj.total_assets == Decimal("123456.78")
    assert obj.cash_and_equivalents == Decimal("12.34")

    # boolean and ints preserved
    assert obj.is_consolidated is True
    assert obj.fiscal_year == 2024


def test_missing_required_fields_raises():
    """必須フィールド欠如で ValidationError が発生することを検証します."""
    payload = sample_payload()
    payload.pop("doc_id")
    with pytest.raises(ValidationError):
        EdinetBalanceSheetCreate(**payload)


def test_field_length_limits_enforced():
    """フィールド長制限が適用されることを検証します."""
    payload = sample_payload()
    payload["doc_id"] = "x" * 51
    with pytest.raises(ValidationError):
        EdinetBalanceSheetCreate(**payload)


def test_latest_schema_minimal():
    """最小限のフィールドで `EdinetBalanceSheetLatest` を生成できることを検証します."""
    latest = EdinetBalanceSheetLatest(
        sec_code="7203", period_end_date=date(2024, 12, 31), total_assets="1.0"
    )
    assert latest.sec_code == "7203"
    assert latest.total_assets == Decimal("1.0")
