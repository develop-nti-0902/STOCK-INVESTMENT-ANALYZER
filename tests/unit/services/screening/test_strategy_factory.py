# -*- coding: utf-8 -*-
"""Test ScreeningStrategyFactory."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services.screening.strategy_factory import ScreeningStrategyFactory


def test_import():
    """Test that the module can be imported."""
    assert ScreeningStrategyFactory is not None


def test_create_requires_screening_service():
    """screening_service が None の場合、ValueError を発生させる。"""
    with pytest.raises(ValueError, match="screening_service is required"):
        ScreeningStrategyFactory.create("01", screening_service=None)


def test_create_with_screening_service():
    """Service 経由で業種設定を取得する。"""
    # ScreeningConfig をモック作成
    mock_config = MagicMock()
    mock_config.industry_code = "01"
    mock_config.industry_name = "水産・農林業"

    # ScreeningService のモック
    mock_service = MagicMock()
    mock_service.get_industry_config.return_value = mock_config

    # Factory で Service 経由に取得
    strategy = ScreeningStrategyFactory.create("01", screening_service=mock_service)

    # 検証
    assert strategy is not None
    mock_service.get_industry_config.assert_called_once_with("01")


def test_create_all_valid_codes_with_service():
    """全業種コードでインスタンスを生成できる（Service 経由）。"""
    # Service をモック
    mock_service = MagicMock()

    for code in [f"{i:02d}" for i in range(1, 34)]:
        mock_config = MagicMock()
        mock_config.industry_code = code
        mock_config.industry_name = f"Industry {code}"
        mock_service.get_industry_config.return_value = mock_config

        strategy = ScreeningStrategyFactory.create(code, screening_service=mock_service)
        assert strategy is not None


def test_create_industry_code_not_found_with_service():
    """Service で業種コードが見つからない場合は ValueError を発生。"""
    # Service が None を返す（キャッシュに該当なし）
    mock_service = MagicMock()
    mock_service.get_industry_config.return_value = None

    # 業種コード "99" は DB に存在しないので ValueError
    with pytest.raises(ValueError, match="Industry code .* not found in database"):
        ScreeningStrategyFactory.create("99", screening_service=mock_service)


def test_create_uses_cache():
    """同一業種コードを2回呼ぶとキャッシュが使用される。"""
    # キャッシュをクリアして新鮮な状態でテスト
    ScreeningStrategyFactory._strategy_cache.clear()

    mock_service = MagicMock()
    mock_config = MagicMock()
    mock_config.industry_code = "05"
    mock_config.industry_name = "繊維製品"
    mock_service.get_industry_config.return_value = mock_config

    ScreeningStrategyFactory.create("05", screening_service=mock_service)
    # キャッシュに保存されているはず
    assert "05" in ScreeningStrategyFactory._strategy_cache

    # 2回目はキャッシュから
    strategy = ScreeningStrategyFactory.create("05", screening_service=mock_service)
    assert strategy is not None


def test_load_custom_strategy_cached():
    """キャッシュ済みの戦略クラスが返る。"""
    ScreeningStrategyFactory._strategy_cache.clear()

    mock_service = MagicMock()
    mock_config = MagicMock()
    mock_config.industry_code = "02"
    mock_config.industry_name = "鉱業"
    mock_service.get_industry_config.return_value = mock_config

    # 一度作成してキャッシュに入れる
    ScreeningStrategyFactory.create("02", screening_service=mock_service)
    klass = ScreeningStrategyFactory._load_custom_strategy("02")
    assert klass is not None
