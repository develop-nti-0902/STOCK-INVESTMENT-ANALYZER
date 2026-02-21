"""`SimpleScreeningService` のユニットテスト.

簡易的なモックと代表的なケースを検証する.
"""

from datetime import date
from types import SimpleNamespace

import pytest

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


class DummyRepo:
    """`ScreeningResultRepository` の代替として upsert 呼び出しを記録するヘルパー."""

    def __init__(self):
        """初期化して呼び出し記録リストを用意する."""
        self.calls = []

    async def upsert(self, payload):
        """upsert 呼び出しを記録する."""
        self.calls.append(payload)


class DummyMaker:
    """`async_sessionmaker` の最低限の振る舞いを提供するスタブ."""

    def __init__(self, session):
        """セッションオブジェクトを保持する."""
        self._session = session

    def __call__(self):
        """コンテキストマネージャを返して with 文に対応する."""
        return self

    def begin(self):
        """トランザクション開始用コンテキストマネージャを返す."""
        return self

    async def __aenter__(self):
        """非同期コンテキストでセッションを返す."""
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        """非同期コンテキストの終了処理を noop で行う."""
        return False


@pytest.mark.asyncio
async def test_evaluate_required_checks_failures():
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

    res = await svc.evaluate("BAD", date(2026, 2, 18))

    assert res.pass_required is False
    assert "eps_health" in res.failed_conditions
    assert "operating_cf" in res.failed_conditions
    assert res.status == "not_eligible"


@pytest.mark.asyncio
async def test_evaluate_full_score_priority():
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

    res = await svc.evaluate("GOOD", date(2026, 2, 18))

    assert res.pass_required is True
    assert res.total_score == 100
    assert res.status == "priority"


@pytest.mark.asyncio
async def test_run_outputs(capsys):
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

    await svc.run(["GOOD", "BAD"], date(2026, 2, 18))

    out, err = capsys.readouterr()
    assert "通過: GOOD" in out
    assert "不合格: BAD" in out
    assert "合格 1件" in out


@pytest.mark.asyncio
async def test_run_persists_results_with_repository():
    """`screening_result_maker` 経由で upsert が呼ばれることを検証する。"""
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
    repo = DummyRepo()
    maker = DummyMaker(session=object())
    svc = SimpleScreeningService(
        fq,
        screening_result_maker=maker,
        screening_result_factory=lambda session: repo,
    )

    await svc.run(["GOOD"], date(2026, 2, 18))

    assert len(repo.calls) == 1
    payload = repo.calls[0]
    assert payload["sec_code"] == "GOOD"
    assert payload["status"] == "priority"
