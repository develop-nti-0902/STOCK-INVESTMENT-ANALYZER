# -*- coding: utf-8 -*-
"""Test BaseScreeningStrategy."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

import pytest

from app.services.screening.base_strategy import BaseScreeningStrategy
from app.services.screening.models import ScreeningConfig, ScreeningScoreConfig, ScreeningThresholds

# ---------------------------------------------------------------------------
# テスト用モックデータクラス
# ---------------------------------------------------------------------------


@dataclass
class MockDiv:
    """テスト用配当データ。"""

    dividend_per_share: Optional[float]
    fiscal_year_end: Optional[date] = None


@dataclass
class MockEps:
    """テスト用EPSデータ。"""

    eps: Optional[float]
    fiscal_year_end: Optional[date] = None


@dataclass
class MockCf:
    """テスト用営業CFデータ。"""

    operating_cf: Optional[float]
    fiscal_year_end: Optional[date] = None


@dataclass
class MockStab:
    """テスト用事業安定性データ。"""

    net_sales: Optional[float]
    operating_income: Optional[float]
    operating_margin: Optional[float]
    fiscal_year_end: Optional[date] = None


# ---------------------------------------------------------------------------
# テスト用具象クラス（抽象メソッドを最低限実装）
# ---------------------------------------------------------------------------


class ConcreteStrategy(BaseScreeningStrategy):
    """テスト用具象スクリーニング戦略。"""

    async def evaluate(self, sec_code: str, _evaluation_date: date, **kwargs: Any):
        """evaluate_with_history を空データで呼び出す。"""
        return await self.evaluate_with_history(sec_code, _evaluation_date, [], [], [], [])


def _make_strategy(
    thresholds: Optional[ScreeningThresholds] = None,
    score_config: Optional[ScreeningScoreConfig] = None,
) -> ConcreteStrategy:
    config = ScreeningConfig(
        industry_code="01",
        industry_name="テスト",
        thresholds=thresholds or ScreeningThresholds(),
        score_config=score_config or ScreeningScoreConfig(),
    )
    return ConcreteStrategy(config)


# ---------------------------------------------------------------------------
# インポート・基本プロパティ
# ---------------------------------------------------------------------------


def test_import():
    """Test that the module can be imported."""
    assert BaseScreeningStrategy is not None


def test_config_property():
    """config プロパティが設定を返すこと。"""
    strategy = _make_strategy()
    assert strategy.config.industry_code == "01"
    assert strategy.config.industry_name == "テスト"


def test_thresholds_and_score_config_assigned():
    """コンストラクタで _thresholds と _score_config が設定されること。"""
    thresholds = ScreeningThresholds(dividend_min_consecutive_increase=5)
    score_config = ScreeningScoreConfig(dividend_max_score=50)
    strategy = _make_strategy(thresholds=thresholds, score_config=score_config)
    assert strategy._thresholds.dividend_min_consecutive_increase == 5
    assert strategy._score_config.dividend_max_score == 50


# ---------------------------------------------------------------------------
# _check_dividend_continuity
# ---------------------------------------------------------------------------


def test_check_dividend_continuity_empty():
    """空の場合は False を返す。"""
    s = _make_strategy()
    assert s._check_dividend_continuity([]) is False


def test_check_dividend_continuity_single():
    """単一レコードのみは False を返す。"""
    s = _make_strategy()
    assert s._check_dividend_continuity([MockDiv(100)]) is False


def test_check_dividend_continuity_decline():
    """減配がある場合は Falseを返す。"""
    s = _make_strategy()
    divs = [MockDiv(100), MockDiv(110), MockDiv(105)]  # 減配あり
    assert s._check_dividend_continuity(divs) is False


def test_check_dividend_continuity_ok():
    """連続増配（デフォルト閾値3年）を満たせば True。"""
    s = _make_strategy()
    divs = [MockDiv(100), MockDiv(110), MockDiv(120), MockDiv(130)]
    assert s._check_dividend_continuity(divs) is True


def test_check_dividend_continuity_none_values_filtered():
    """None 値は除外して判定すること。"""
    s = _make_strategy()
    divs = [MockDiv(None), MockDiv(100), MockDiv(110), MockDiv(120)]
    assert s._check_dividend_continuity(divs) is True


def test_check_dividend_continuity_threshold_not_met():
    """連続増配年数が閾値未満のとき False。"""
    thresholds = ScreeningThresholds(dividend_min_consecutive_increase=5)
    s = _make_strategy(thresholds=thresholds)
    divs = [MockDiv(100), MockDiv(110), MockDiv(120)]  # 連続3年だが閾値5年
    assert s._check_dividend_continuity(divs) is False


# ---------------------------------------------------------------------------
# _check_eps_health
# ---------------------------------------------------------------------------


def test_check_eps_health_empty():
    """空の場合は False を返す。"""
    s = _make_strategy()
    assert s._check_eps_health([]) is False


def test_check_eps_health_zero_eps():
    """EPSが0の場合は False を返す。"""
    s = _make_strategy()
    assert s._check_eps_health([MockEps(0)]) is False


def test_check_eps_health_negative():
    """負のEPSがある場合は False を返す。"""
    s = _make_strategy()
    assert s._check_eps_health([MockEps(-10), MockEps(20)]) is False


def test_check_eps_health_ok():
    """全て正のEPSで増加傾向なら True を返す。"""
    s = _make_strategy()
    eps = [MockEps(100), MockEps(110), MockEps(120), MockEps(130), MockEps(140)]
    assert s._check_eps_health(eps) is True


def test_check_eps_health_consecutive_decline_exceeded():
    """連続減少が閾値超過の場合 False。"""
    thresholds = ScreeningThresholds(eps_max_consecutive_decline=1)
    s = _make_strategy(thresholds=thresholds)
    eps = [MockEps(100), MockEps(90), MockEps(80), MockEps(70)]  # 3連続減
    assert s._check_eps_health(eps) is False


def test_check_eps_health_decline_rate_exceeded():
    """減少率が閾値超過の場合 False。"""
    thresholds = ScreeningThresholds(eps_decline_max_rate=0.30)
    s = _make_strategy(thresholds=thresholds)
    # 100 -> 50 は50%減（閾値30%超）
    eps = [MockEps(100), MockEps(50)]
    assert s._check_eps_health(eps) is False


def test_check_eps_health_none_values_filtered():
    """None 値は除外して判定すること。"""
    s = _make_strategy()
    eps = [MockEps(None), MockEps(100), MockEps(110)]
    assert s._check_eps_health(eps) is True


# ---------------------------------------------------------------------------
# _check_operating_cf
# ---------------------------------------------------------------------------


def test_check_operating_cf_empty():
    """空の場合は False を返す。"""
    s = _make_strategy()
    assert s._check_operating_cf([]) is False


def test_check_operating_cf_insufficient_positive():
    """プラス年数が閾値未満の場合 False。"""
    thresholds = ScreeningThresholds(cf_min_positive_years=4)
    s = _make_strategy(thresholds=thresholds)
    cfs = [MockCf(-100), MockCf(50), MockCf(60), MockCf(-10)]  # プラス2年
    assert s._check_operating_cf(cfs) is False


def test_check_operating_cf_ok():
    """プラス年数が閾値以上の場合 True を返す。"""
    thresholds = ScreeningThresholds(cf_min_positive_years=4)
    s = _make_strategy(thresholds=thresholds)
    cfs = [MockCf(100), MockCf(50), MockCf(60), MockCf(70)]  # プラス4年
    assert s._check_operating_cf(cfs) is True


def test_check_operating_cf_none_values_filtered():
    """None 値は除外して判定すること。"""
    thresholds = ScreeningThresholds(cf_min_positive_years=1)
    s = _make_strategy(thresholds=thresholds)
    cfs = [MockCf(None), MockCf(50)]
    assert s._check_operating_cf(cfs) is True


# ---------------------------------------------------------------------------
# _score_dividend
# ---------------------------------------------------------------------------


def test_score_dividend_empty():
    """空の場合はスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_dividend([]) == 0


def test_score_dividend_single():
    """単一レコードのみはスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_dividend([MockDiv(100)]) == 0


def test_score_dividend_all_increasing():
    """全期間増配でスコアが加算される。"""
    sc = ScreeningScoreConfig(
        dividend_all_increase_score=10,
        dividend_growth_rate_threshold=0.0,
        dividend_growth_rate_score=0,
        dividend_tau_threshold=100.0,  # 到達不能な閾値
        dividend_tau_score=0,
        dividend_max_score=30,
    )
    s = _make_strategy(score_config=sc)
    divs = [MockDiv(100), MockDiv(110), MockDiv(120)]
    assert s._score_dividend(divs) == 10


def test_score_dividend_growth_rate():
    """増配率が閾値以上のときスコアが加算。"""
    sc = ScreeningScoreConfig(
        dividend_all_increase_score=0,
        dividend_growth_rate_threshold=0.05,
        dividend_growth_rate_score=10,
        dividend_tau_threshold=100.0,
        dividend_tau_score=0,
        dividend_max_score=30,
    )
    s = _make_strategy(score_config=sc)
    # 100->110 は10%増
    divs = [MockDiv(100), MockDiv(110)]
    assert s._score_dividend(divs) == 10


def test_score_dividend_max_capped():
    """スコアが max_score を超えないこと。"""
    sc = ScreeningScoreConfig(
        dividend_all_increase_score=20,
        dividend_growth_rate_threshold=0.0,
        dividend_growth_rate_score=20,
        dividend_tau_threshold=0.0,
        dividend_tau_score=20,
        dividend_max_score=30,
    )
    s = _make_strategy(score_config=sc)
    divs = [MockDiv(100), MockDiv(110), MockDiv(120)]
    assert s._score_dividend(divs) <= 30


# ---------------------------------------------------------------------------
# _score_eps
# ---------------------------------------------------------------------------


def test_score_eps_empty():
    """空の場合はスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_eps([]) == 0


def test_score_eps_single():
    """単一レコードのみはスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_eps([MockEps(100)]) == 0


def test_score_eps_growth_years():
    """増加年数が閾値以上でスコアが加算。"""
    sc = ScreeningScoreConfig(
        eps_growth_years_threshold=3,
        eps_growth_years_score=10,
        eps_consecutive_growth_threshold=100,  # 到達不能
        eps_consecutive_growth_score=0,
        eps_tau_threshold=100.0,
        eps_tau_score=0,
        eps_max_score=30,
    )
    s = _make_strategy(score_config=sc)
    eps = [MockEps(100), MockEps(110), MockEps(120), MockEps(130)]  # 3回増加
    assert s._score_eps(eps) == 10


def test_score_eps_consecutive_growth():
    """N年連続EPS増加でスコアが加算。"""
    sc = ScreeningScoreConfig(
        eps_growth_years_threshold=100,  # 到達不能
        eps_growth_years_score=0,
        eps_consecutive_growth_threshold=3,
        eps_consecutive_growth_score=10,
        eps_tau_threshold=100.0,
        eps_tau_score=0,
        eps_max_score=30,
    )
    s = _make_strategy(score_config=sc)
    eps = [MockEps(100), MockEps(110), MockEps(120), MockEps(130)]
    assert s._score_eps(eps) == 10


def test_score_eps_max_capped():
    """スコアが max_score を超えないこと。"""
    sc = ScreeningScoreConfig(
        eps_growth_years_threshold=1,
        eps_growth_years_score=20,
        eps_consecutive_growth_threshold=1,
        eps_consecutive_growth_score=20,
        eps_tau_threshold=0.0,
        eps_tau_score=20,
        eps_max_score=30,
    )
    s = _make_strategy(score_config=sc)
    eps = [MockEps(100), MockEps(110), MockEps(120), MockEps(130)]
    assert s._score_eps(eps) <= 30


# ---------------------------------------------------------------------------
# _score_stability
# ---------------------------------------------------------------------------


def test_score_stability_empty():
    """空の場合はスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_stability([]) == 0


def test_score_stability_single():
    """単一レコードのみはスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_stability([MockStab(100, 10, 0.1)]) == 0


def test_score_stability_sales_growth():
    """売上成長年数が閾値以上でスコア加算。"""
    sc = ScreeningScoreConfig(
        stability_sales_growth_threshold=3,
        stability_sales_growth_score=10,
        stability_margin_growth_threshold=100,  # 到達不能
        stability_margin_growth_score=0,
        stability_max_score=20,
    )
    s = _make_strategy(score_config=sc)
    stabs = [
        MockStab(100, 10, 0.1),
        MockStab(110, 11, 0.1),
        MockStab(120, 12, 0.1),
        MockStab(130, 13, 0.1),
    ]
    assert s._score_stability(stabs) == 10


def test_score_stability_income_growth():
    """利益成長年数が閾値以上でスコア加算。"""
    sc = ScreeningScoreConfig(
        stability_sales_growth_threshold=100,  # 到達不能
        stability_sales_growth_score=0,
        stability_margin_growth_threshold=3,
        stability_margin_growth_score=10,
        stability_max_score=20,
    )
    s = _make_strategy(score_config=sc)
    stabs = [
        MockStab(100, 10, 0.1),
        MockStab(100, 12, 0.12),
        MockStab(100, 14, 0.14),
        MockStab(100, 16, 0.16),
    ]
    assert s._score_stability(stabs) == 10


# ---------------------------------------------------------------------------
# _score_profitability
# ---------------------------------------------------------------------------


def test_score_profitability_empty():
    """空の場合はスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_profitability([]) == 0


def test_score_profitability_single():
    """単一レコードのみはスコア 0 を返す。"""
    s = _make_strategy()
    assert s._score_profitability([MockStab(100, 10, 0.1)]) == 0


def test_score_profitability_no_decline():
    """マージン低下年数が閾値以内でスコア加算。"""
    sc = ScreeningScoreConfig(
        profitability_decline_years_threshold=2,
        profitability_decline_score=10,
        profitability_consecutive_decline_threshold=2.0,
        profitability_consecutive_decline_score=10,
        profitability_max_score=20,
    )
    s = _make_strategy(score_config=sc)
    stabs = [
        MockStab(100, 10, 10.0),
        MockStab(100, 11, 11.0),
        MockStab(100, 12, 12.0),
    ]
    assert s._score_profitability(stabs) >= 10


def test_score_profitability_consecutive_decline():
    """2pt以上の連続マージン低下があると特定スコアが0になる。"""
    sc = ScreeningScoreConfig(
        profitability_decline_years_threshold=10,  # 到達不能
        profitability_decline_score=0,
        profitability_consecutive_decline_threshold=2.0,
        profitability_consecutive_decline_score=10,
        profitability_max_score=20,
    )
    s = _make_strategy(score_config=sc)
    # 2pt以上の連続低下2年
    stabs = [
        MockStab(100, 10, 20.0),
        MockStab(100, 10, 17.0),  # -3pt
        MockStab(100, 10, 14.0),  # -3pt（連続）
    ]
    assert s._score_profitability(stabs) == 0


def test_score_profitability_max_capped():
    """スコアが max_score を超えないこと。"""
    sc = ScreeningScoreConfig(
        profitability_decline_years_threshold=10,
        profitability_decline_score=15,
        profitability_consecutive_decline_threshold=2.0,
        profitability_consecutive_decline_score=15,
        profitability_max_score=20,
    )
    s = _make_strategy(score_config=sc)
    stabs = [MockStab(100, 10, 10.0), MockStab(100, 11, 11.0)]
    assert s._score_profitability(stabs) <= 20


# ---------------------------------------------------------------------------
# _calculate_average_growth_rate
# ---------------------------------------------------------------------------


def test_calculate_average_growth_rate_single():
    """単一値の場合は 0.0 を返す。"""
    s = _make_strategy()
    assert s._calculate_average_growth_rate([100.0]) == 0.0


def test_calculate_average_growth_rate_basic():
    """基本的な成長率計算（100->110: 10%）。"""
    s = _make_strategy()
    rate = s._calculate_average_growth_rate([100.0, 110.0])
    assert abs(rate - 0.1) < 1e-9


def test_calculate_average_growth_rate_zero_base():
    """ベース値が0の場合は除外される。"""
    s = _make_strategy()
    rate = s._calculate_average_growth_rate([0.0, 100.0])
    assert rate == 0.0


def test_calculate_average_growth_rate_no_valid():
    """有効な計算対象がない場合は 0.0 を返す。"""
    s = _make_strategy()
    assert s._calculate_average_growth_rate([0.0, 0.0]) == 0.0


# ---------------------------------------------------------------------------
# _kendall_tau
# ---------------------------------------------------------------------------


def test_kendall_tau_single():
    """単一値の場合は 0.0 を返す。"""
    s = _make_strategy()
    assert s._kendall_tau([1.0]) == 0.0


def test_kendall_tau_monotone_increasing():
    """単調増加の場合は 1.0 を返す。"""
    s = _make_strategy()
    tau = s._kendall_tau([1.0, 2.0, 3.0, 4.0])
    assert tau == 1.0


def test_kendall_tau_monotone_decreasing():
    """単調減少の場合は -1.0 を返す。"""
    s = _make_strategy()
    tau = s._kendall_tau([4.0, 3.0, 2.0, 1.0])
    assert tau == -1.0


def test_kendall_tau_all_equal():
    """全て等しい場合は 0.0 を返す（concordant=discordant=0）。"""
    s = _make_strategy()
    tau = s._kendall_tau([5.0, 5.0, 5.0])
    assert tau == 0.0


# ---------------------------------------------------------------------------
# _resolve_status
# ---------------------------------------------------------------------------


def test_resolve_status_not_eligible_failed_required():
    """必須条件失敗時は not_eligible を返す。"""
    s = _make_strategy()
    assert s._resolve_status(False, 100) == "not_eligible"


def test_resolve_status_priority():
    """スコアが priority 閾値以上なら priority を返す。"""
    sc = ScreeningScoreConfig(
        status_priority_threshold=90,
        status_active_threshold=80,
        status_watch_threshold=70,
    )
    s = _make_strategy(score_config=sc)
    assert s._resolve_status(True, 95) == "priority"


def test_resolve_status_active():
    """スコアが active 閾値内なら active を返す。"""
    sc = ScreeningScoreConfig(
        status_priority_threshold=90,
        status_active_threshold=80,
        status_watch_threshold=70,
    )
    s = _make_strategy(score_config=sc)
    assert s._resolve_status(True, 85) == "active"


def test_resolve_status_watch():
    """スコアが watch 閾値内なら watch を返す。"""
    sc = ScreeningScoreConfig(
        status_priority_threshold=90,
        status_active_threshold=80,
        status_watch_threshold=70,
    )
    s = _make_strategy(score_config=sc)
    assert s._resolve_status(True, 75) == "watch"


def test_resolve_status_not_eligible_low_score():
    """スコアが watch 閾値未満なら not_eligible を返す。"""
    sc = ScreeningScoreConfig(
        status_priority_threshold=90,
        status_active_threshold=80,
        status_watch_threshold=70,
    )
    s = _make_strategy(score_config=sc)
    assert s._resolve_status(True, 60) == "not_eligible"


# ---------------------------------------------------------------------------
# _extract_latest_fiscal_year_end
# ---------------------------------------------------------------------------


def test_extract_fy_all_empty():
    """全データ空の場合は None を返す。"""
    result = BaseScreeningStrategy._extract_latest_fiscal_year_end([], [], [])
    assert result is None


def test_extract_fy_from_stabs():
    """stabs から最新の fiscal_year_end を取得する。"""
    stabs = [MockStab(100, 10, 0.1, fiscal_year_end=date(2024, 3, 31))]
    result = BaseScreeningStrategy._extract_latest_fiscal_year_end([], [], stabs)
    assert result == date(2024, 3, 31)


def test_extract_fy_from_divs_when_stabs_empty():
    """stabs が空の場合は divs から取得する。"""
    divs = [MockDiv(100, fiscal_year_end=date(2023, 12, 31))]
    result = BaseScreeningStrategy._extract_latest_fiscal_year_end(divs, [], [])
    assert result == date(2023, 12, 31)


def test_extract_fy_none_attribute():
    """fiscal_year_end が None の場合は次のソースを参照。"""
    stabs = [MockStab(100, 10, 0.1, fiscal_year_end=None)]
    divs = [MockDiv(100, fiscal_year_end=date(2023, 12, 31))]
    result = BaseScreeningStrategy._extract_latest_fiscal_year_end(divs, [], stabs)
    # stabs が先に試されるが None → divs へ
    # ただし実装は stabs[-1].fiscal_year_end が None なら次のソースへ行く
    assert result == date(2023, 12, 31)


# ---------------------------------------------------------------------------
# evaluate_with_history（統合）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_with_history_empty_data():
    """全データ空の場合、必須条件失敗で not_eligible。"""
    s = _make_strategy()
    result = await s.evaluate_with_history("1234", date(2024, 3, 31), [], [], [], [])
    assert result.sec_code == "1234"
    assert result.pass_required is False
    assert result.status == "not_eligible"


@pytest.mark.asyncio
async def test_evaluate_with_history_passes_all():
    """十分なデータがあれば pass_required が Trueになりうる。"""
    thresholds = ScreeningThresholds(
        dividend_min_consecutive_increase=3,
        eps_max_consecutive_decline=1,
        eps_decline_max_rate=0.50,
        cf_min_positive_years=3,
    )
    s = _make_strategy(thresholds=thresholds)
    fy = date(2024, 3, 31)
    divs = [MockDiv(100, fy), MockDiv(110, fy), MockDiv(120, fy), MockDiv(130, fy)]
    eps = [MockEps(100, fy), MockEps(110, fy), MockEps(120, fy), MockEps(130, fy)]
    cfs = [MockCf(50, fy), MockCf(60, fy), MockCf(70, fy), MockCf(80, fy)]
    stabs = [
        MockStab(100, 10, 0.1, fy),
        MockStab(110, 11, 0.1, fy),
        MockStab(120, 12, 0.1, fy),
        MockStab(130, 13, 0.1, fy),
    ]
    result = await s.evaluate_with_history("1234", date(2024, 3, 31), divs, eps, cfs, stabs)
    assert result.pass_required is True
    assert result.fiscal_year_end == fy


@pytest.mark.asyncio
async def test_evaluate_with_history_failed_conditions_listed():
    """必須条件失敗時に failed_conditions に項目が含まれる。"""
    s = _make_strategy()
    result = await s.evaluate_with_history("9999", date(2024, 3, 31), [], [], [], [])
    assert "dividend_continuity" in result.failed_conditions
    assert "eps_health" in result.failed_conditions
    assert "operating_cf" in result.failed_conditions
