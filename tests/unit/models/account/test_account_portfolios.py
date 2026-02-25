"""AccountPortfolios モデルの単体テスト."""

from __future__ import annotations

from app.models.account import account_portfolios


def test_account_portfolios_defaults_and_repr():
    """デフォルト値と repr 表示を検証する."""
    # quantity のカラムデフォルトはコンストラクタ時に自動で埋まらないため明示する
    inst = account_portfolios.AccountPortfolios(account_id=42, symbol="7203.T", quantity=0)

    assert inst.account_id == 42
    assert inst.symbol == "7203.T"
    assert inst.quantity == 0
    assert inst.avg_price is None
    assert inst.market_value is None
    assert inst.currency is None
    assert inst.portfolio_name is None

    r = repr(inst)
    assert "7203.T" in r
