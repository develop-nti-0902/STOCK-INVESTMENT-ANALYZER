"""Unit tests for EdinetCashFlowStatement model."""

from __future__ import annotations

import inspect

from app.models.market_data.edinet import EdinetCashFlowStatement


def test_tablename_and_columns_exist():
    """テーブル名と主要カラムが存在することを検証する."""
    assert getattr(EdinetCashFlowStatement, "__tablename__") == "edinet_cash_flow_statement"

    expected_attrs = [
        "doc_id",
        "sec_code",
        "submission_date",
        "period_end_date",
        "operating_cf",
        "candidate_contexts",
        "is_consolidated",
    ]

    for attr in expected_attrs:
        assert hasattr(EdinetCashFlowStatement, attr), f"Missing attribute: {attr}"


def test_table_args_contains_unique_constraint():
    """__table_args__ にユニーク制約が含まれることを検証する."""
    table_args = getattr(EdinetCashFlowStatement, "__table_args__", None)
    assert table_args is not None

    uc_found = any(getattr(t, "name", None) == "uq_edinet_cfs_sec_period" for t in table_args)
    assert uc_found, "UniqueConstraint 'uq_edinet_cfs_sec_period' not found in __table_args__"


def test_repr_signature():
    """__repr__ のシグネチャが期待どおりであることを検証する."""
    sig = inspect.signature(EdinetCashFlowStatement.__repr__)
    assert len(sig.parameters) == 1
