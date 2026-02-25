"""Tests for the `account_transactions` model."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.account import account_transactions


def test_account_transactions_required_fields_and_repr():
    """Verify required fields and repr for AccountTransactions model."""
    now = datetime.now(timezone.utc)
    inst = account_transactions.AccountTransactions(
        account_id=1, transaction_type="BUY", executed_at=now
    )

    assert inst.account_id == 1
    assert inst.transaction_type == "BUY"
    assert inst.executed_at == now
    assert inst.symbol is None
    assert inst.quantity is None

    r = repr(inst)
    assert "BUY" in r
