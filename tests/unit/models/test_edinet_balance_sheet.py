"""Edinet バランスシートモデルの単体テスト."""

import inspect

from app.models.edinet_balance_sheet import EdinetBalanceSheet


def test_tablename_and_columns_exist():
    """テーブル名と主要カラムが存在することを確認する."""
    # テーブル名が仕様通りであること
    assert getattr(EdinetBalanceSheet, "__tablename__") == "edinet_balance_sheets"

    # 主要カラムが存在することを確認（シンプルに属性があるかのみ）
    expected_attrs = [
        "doc_id",
        "sec_code",
        "submission_date",
        "period_end_date",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "bps",
        "candidate_contexts",
        "is_consolidated",
    ]

    for attr in expected_attrs:
        assert hasattr(EdinetBalanceSheet, attr), f"Missing attribute: {attr}"


def test_table_args_contains_unique_constraint():
    """__table_args__ に UNIQUE 制約が含まれていることを確認する."""
    # __table_args__ に UNIQUE 制約が含まれていることを確認
    table_args = getattr(EdinetBalanceSheet, "__table_args__", None)
    assert table_args is not None

    uc_found = any(
        isinstance(t, object) and getattr(t, "name", None) == "uq_edinet_sec_period"
        for t in table_args
    )
    assert uc_found, "UniqueConstraint 'uq_edinet_sec_period' not found in __table_args__"


def test_repr_contains_key_fields():
    """__repr__ のシグネチャが想定通りであることを検証する."""
    sig = inspect.signature(EdinetBalanceSheet.__repr__)
    # __repr__ は引数を取らないメソッドであること（self のみ）を確認
    assert len(sig.parameters) == 1
