"""`SimpleScreeningService` のユニットテスト.

簡易的なモックと代表的なケースを検証する.
"""

from datetime import date
from types import SimpleNamespace

from app.services.screening.simple_screening_service import SimpleScreeningService


class MockFQ:
    """テスト用の簡易 FinancialQueryService モック."""

    def __init__(self, mapping):
        """マッピングを受け取り内部に保持する."""
        self.mapping = mapping

    def get_dividend_history(self, sec_code, years=5):
        """配当履歴を返す."""
        return self.mapping.get(sec_code, {}).get("dividend", [])

    def get_eps_history(self, sec_code, years=5):
        """EPS 履歴を返す."""
        return self.mapping.get(sec_code, {}).get("eps", [])

    def get_operating_cf_history(self, sec_code, years=5):
        """営業CF履歴を返す."""
        return self.mapping.get(sec_code, {}).get("cf", [])

    def get_stability_history(self, sec_code, years=5):
        """事業安定性関連の履歴を返す."""
        return self.mapping.get(sec_code, {}).get("stab", [])


def make_records(values, attr_name):
    """与えられた値リストから SimpleNamespace のリストを作成するユーティリティ."""
    return [SimpleNamespace(**{attr_name: v}) for v in values]


def test_evaluate_required_checks_failures():
    """必須条件チェックに失敗するケースを検証する."""
    mapping = {
        "BAD": {
            "dividend": make_records([5, 4, 3, 2, 1], "dividend_per_share"),
            "eps": make_records([1, 0, -1, -2, -3], "eps"),
            "cf": make_records([-1, -2, -3, -4, -5], "operating_cf"),
            "stab": make_records([10, 9, 8, 7, 6], "net_sales"),
        }
    }
    fq = MockFQ(mapping)
    svc = SimpleScreeningService(fq)

    res = svc.evaluate("BAD", date(2026, 2, 18))

    assert res.pass_required is False
    assert "eps_health" in res.failed_conditions
    assert "operating_cf" in res.failed_conditions
    assert res.status == "not_eligible"


def test_evaluate_full_score_priority():
    """全ての加点条件を満たしてフルスコア（priority）となるケースを検証する."""
    mapping = {
        "GOOD": {
            "dividend": make_records([1, 2, 3, 4, 5], "dividend_per_share"),
            "eps": make_records([1, 2, 3, 4, 5], "eps"),
            "cf": make_records([1, 2, 3, 4, 5], "operating_cf"),
            "stab": [
                SimpleNamespace(net_sales=10 + i, operating_income=1 + i, operating_margin=5.0)
                for i in range(5)
            ],
        }
    }
    fq = MockFQ(mapping)
    svc = SimpleScreeningService(fq)

    res = svc.evaluate("GOOD", date(2026, 2, 18))

    assert res.pass_required is True
    assert res.total_score == 100
    assert res.status == "priority"


def test_run_outputs(capsys):
    """`run()` の標準出力フォーマットを検証する."""
    mapping = {
        "GOOD": {
            "dividend": make_records([1, 2, 3, 4, 5], "dividend_per_share"),
            "eps": make_records([1, 2, 3, 4, 5], "eps"),
            "cf": make_records([1, 2, 3, 4, 5], "operating_cf"),
            "stab": [
                SimpleNamespace(net_sales=10 + i, operating_income=1 + i, operating_margin=5.0)
                for i in range(5)
            ],
        },
        "BAD": {
            "dividend": make_records([5, 4, 3, 2, 1], "dividend_per_share"),
            "eps": make_records([1, 0, -1, -2, -3], "eps"),
            "cf": make_records([-1, -2, -3, -4, -5], "operating_cf"),
            "stab": make_records([10, 9, 8, 7, 6], "net_sales"),
        },
    }
    fq = MockFQ(mapping)
    svc = SimpleScreeningService(fq)

    svc.run(["GOOD", "BAD"], date(2026, 2, 18))

    out, err = capsys.readouterr()
    assert "通過銘柄" in out
    assert "GOOD" in out
    assert "不合格" in out
    assert "BAD" in out
