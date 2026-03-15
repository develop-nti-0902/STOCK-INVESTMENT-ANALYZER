"""Tests for EdinetDividendMetrics Pydantic schemas."""

from datetime import date

from app.schemas.market_data.edinet import EdinetDividendMetricsCreate


def test_schema_instantiation_minimal():
    """最小プロパティでスキーマを生成できることを確認する。"""
    obj = EdinetDividendMetricsCreate(
        edinet_document_id=1,
        period_end_date=date(2025, 3, 31),
    )
    assert obj.edinet_document_id == 1
    assert obj.period_end_date == date(2025, 3, 31)
    # optional fields default to None
    assert obj.dividend_actual is None
    assert obj.eps is None
    assert obj.payout_ratio is None
