# -*- coding: utf-8 -*-
"""Test ScreeningStrategyFactory."""
from __future__ import annotations

import pytest

from app.services.screening.models import ScreeningScoreConfig, ScreeningThresholds
from app.services.screening.strategy_factory import ScreeningStrategyFactory


def test_import():
    """Test that the module can be imported."""
    assert ScreeningStrategyFactory is not None


def test_create_valid_industry_code():
    """有効な業種コードでインスタンスが生成される。"""
    strategy = ScreeningStrategyFactory.create("01")
    assert strategy is not None


def test_create_all_valid_codes():
    """全業種コードでインスタンスを生成できる。"""
    for code in [f"{i:02d}" for i in range(1, 34)]:
        strategy = ScreeningStrategyFactory.create(code)
        assert strategy is not None


def test_create_invalid_code_raises_value_error():
    """無効な業種コードは ValueError を送出する。"""
    with pytest.raises(ValueError, match="Invalid industry_code"):
        ScreeningStrategyFactory.create("99")


def test_create_uses_cache():
    """同一業種コードを2回呼ぶとキャッシュが使用される。"""
    # キャッシュをクリアして新鮮な状態でテスト
    ScreeningStrategyFactory._strategy_cache.clear()
    ScreeningStrategyFactory.create("05")
    # キャッシュに保存されているはず
    assert "05" in ScreeningStrategyFactory._strategy_cache
    # 2回目はキャッシュから
    strategy = ScreeningStrategyFactory.create("05")
    assert strategy is not None


def test_get_config_valid():
    """有効な業種コードで ScreeningConfig が取得できる。"""
    config = ScreeningStrategyFactory.get_config("01")
    assert config.industry_code == "01"
    assert config.industry_name == "水産・農林業"


def test_get_config_invalid_raises():
    """無効な業種コードは ValueError を送出する。"""
    with pytest.raises(ValueError, match="Invalid industry_code"):
        ScreeningStrategyFactory.get_config("00")


def test_customize_config_defaults():
    """カスタム設定なしでは元の設定のコピーが返る。"""
    config = ScreeningStrategyFactory.customize_config("01")
    base = ScreeningStrategyFactory.get_config("01")
    assert config.industry_code == base.industry_code
    assert config.industry_name == base.industry_name


def test_customize_config_with_thresholds():
    """カスタム閾値が反映される。"""
    custom_thresholds = ScreeningThresholds(dividend_min_consecutive_increase=10)
    config = ScreeningStrategyFactory.customize_config("01", thresholds=custom_thresholds)
    assert config.thresholds.dividend_min_consecutive_increase == 10


def test_customize_config_with_score_config():
    """カスタムスコア設定が反映される。"""
    custom_score = ScreeningScoreConfig(dividend_max_score=99)
    config = ScreeningStrategyFactory.customize_config("01", score_config=custom_score)
    assert config.score_config.dividend_max_score == 99


def test_customize_config_invalid_code():
    """無効業種コードは ValueError を送出。"""
    with pytest.raises(ValueError):
        ScreeningStrategyFactory.customize_config("99")


def test_load_custom_strategy_cached():
    """キャッシュ済みの戦略クラスが返る。"""
    ScreeningStrategyFactory._strategy_cache.clear()
    # 一度作成してキャッシュに入れる
    ScreeningStrategyFactory.create("02")
    klass = ScreeningStrategyFactory._load_custom_strategy("02")
    assert klass is not None
