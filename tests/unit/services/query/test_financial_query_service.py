"""FinancialQueryService unit tests.

このモジュールは `FinancialQueryService` の各メソッドが期待通りに
時系列データを古い順で返すことを検証します.
"""

import datetime

from app.services.query.financial_query_service import (
    CfRecord,
    DividendRecord,
    EpsRecord,
    FinancialQueryService,
    StabilityRecord,
)


class MockDividendRepo:
    """Mock: Dividend repository.

    `list_dividends(sec_code)` を提供する簡易実装.
    """

    def __init__(self, data):
        """コンストラクタ."""
        self._data = data

    def list_dividends(self, sec_code):
        """指定した証券コードの配当データリストを返す."""
        return self._data


class MockPLRepo:
    """Mock: Profit and loss repository.

    `list_profit_and_loss(sec_code)` を提供する簡易実装.
    """

    def __init__(self, data):
        """コンストラクタ."""
        self._data = data

    def list_profit_and_loss(self, sec_code):
        """指定した証券コードの損益データリストを返す."""
        return self._data


class MockCFRepo:
    """Mock: Cash flow repository.

    `list_cash_flows(sec_code)` を提供する簡易実装.
    """

    def __init__(self, data):
        """コンストラクタ."""
        self._data = data

    def list_cash_flows(self, sec_code):
        """指定した証券コードのキャッシュフローデータリストを返す."""
        return self._data


def make_record(year, **kwargs):
    """テスト用に fiscal_year_end を持つ辞書レコードを作るユーティリティ."""
    d = {"fiscal_year_end": datetime.date(year, 3, 31)}
    d.update(kwargs)
    return d


def test_get_dividend_history_sorted_and_limited():
    """最新N年の配当データが古い順で返ることを検証する."""
    data = [
        make_record(2022, dividend_per_share=30.0),
        make_record(2019, dividend_per_share=20.0),
        make_record(2020, dividend_per_share=22.0),
        make_record(2021, dividend_per_share=25.0),
    ]
    service = FinancialQueryService(MockDividendRepo(data), MockPLRepo([]), MockCFRepo([]))
    res = service.get_dividend_history("7203", years=3)
    assert len(res) == 3
    # 古い順で並んでいること
    assert res[0].fiscal_year_end < res[1].fiscal_year_end < res[2].fiscal_year_end
    assert isinstance(res[0], DividendRecord)
    assert res[0].dividend_per_share == 22.0


def test_get_eps_history_and_values():
    """EPS履歴が正しく抽出・変換されることを検証する."""
    data = [
        make_record(2018, eps=50.0),
        make_record(2019, eps=55.0),
        make_record(2020, eps=60.0),
    ]
    service = FinancialQueryService(MockDividendRepo([]), MockPLRepo(data), MockCFRepo([]))
    res = service.get_eps_history("6758", years=5)
    assert len(res) == 3
    assert all(isinstance(x, EpsRecord) for x in res)
    assert [r.eps for r in res] == [50.0, 55.0, 60.0]


def test_get_operating_cf_history():
    """営業キャッシュフロー履歴を古い順で返すことを検証する."""
    data = [
        make_record(2020, operating_cf=1000.0),
        make_record(2019, operating_cf=900.0),
    ]
    service = FinancialQueryService(MockDividendRepo([]), MockPLRepo([]), MockCFRepo(data))
    res = service.get_operating_cf_history("9999", years=5)
    assert len(res) == 2
    assert isinstance(res[0], CfRecord)
    assert [r.operating_cf for r in res] == [900.0, 1000.0]


def test_get_stability_history_computes_margin():
    """売上と営業利益から営業利益率が計算されることを検証する."""
    data = [
        make_record(2019, net_sales=100.0, operating_income=10.0),
        make_record(2020, net_sales=200.0, operating_income=30.0),
    ]
    service = FinancialQueryService(MockDividendRepo([]), MockPLRepo(data), MockCFRepo([]))
    res = service.get_stability_history("7203", years=2)
    assert len(res) == 2
    assert isinstance(res[0], StabilityRecord)
    assert abs(res[0].operating_margin - 0.1) < 1e-9
    assert abs(res[1].operating_margin - 0.15) < 1e-9
