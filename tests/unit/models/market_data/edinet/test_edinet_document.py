"""Unit tests for app.models.edinet_document."""

from __future__ import annotations

from datetime import date

from app.models.market_data.edinet import EdinetDocument


def test_model_repr_contains_key_fields():
    """モデルの repr が主要フィールドを含むことを検証する."""
    m = EdinetDocument(
        doc_id="S0000001234",
        sec_code="1234567890",
        submission_date=date(2024, 3, 31),
        report_type="annual",
    )

    r = repr(m)
    assert "doc_id" in r
    assert "sec_code" in r


def test_edinet_document_initialization():
    """EdinetDocument モデルの初期化を検証する."""
    m = EdinetDocument(
        doc_id="S0000001234",
        sec_code="1234567890",
        submission_date=date(2024, 3, 31),
        report_type="quarterly",
        candidate_contexts="NonConsolidated",
        candidate_keys="CurrentYearDuration",
    )

    assert m.doc_id == "S0000001234"
    assert m.sec_code == "1234567890"
    assert m.submission_date == date(2024, 3, 31)
    assert m.report_type == "quarterly"
    assert m.candidate_contexts == "NonConsolidated"
    assert m.candidate_keys == "CurrentYearDuration"
