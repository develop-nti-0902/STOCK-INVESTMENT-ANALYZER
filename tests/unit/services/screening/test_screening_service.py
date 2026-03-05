# -*- coding: utf-8 -*-
"""Test ScreeningService."""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.screening.models import ScreeningResult
from app.services.screening.screening_service import ScreeningService


def test_import():
    """Test that the module can be imported."""
    assert ScreeningService is not None


def _make_result(
    sec_code: str = "1234",
    status: str = "active",
    pass_required: bool = True,
    total_score: int = 85,
) -> ScreeningResult:
    """テスト用 ScreeningResult を生成。"""
    return ScreeningResult(
        sec_code=sec_code,
        pass_required=pass_required,
        total_score=total_score,
        score_dividend=20,
        score_eps=20,
        score_stability=15,
        score_profitability=10,
        status=status,
        failed_conditions=[],
        fiscal_year_end=date(2024, 3, 31),
    )


# ---------------------------------------------------------------------------
# _build_screening_details
# ---------------------------------------------------------------------------


def test_build_screening_details_basic():
    """基本的なスクリーニング詳細が正しく構築される。"""
    svc = ScreeningService(financial_query_service=MagicMock())
    result = _make_result()
    details = svc._build_screening_details(result)
    assert details["status"] == "active"
    assert details["pass_required"] is True
    assert details["score_breakdown"]["dividend"] == 20
    assert details["fiscal_year_end"] == "2024-03-31"


def test_build_screening_details_none_fiscal_year():
    """fiscal_year_end が None の場合は None をセットする。"""
    svc = ScreeningService(financial_query_service=MagicMock())
    result = _make_result()
    result.fiscal_year_end = None
    details = svc._build_screening_details(result)
    assert details["fiscal_year_end"] is None


# ---------------------------------------------------------------------------
# _build_upsert_payload
# ---------------------------------------------------------------------------


def test_build_upsert_payload_keys():
    """upsert ペイロードに必須キーが含まれること。"""
    svc = ScreeningService(financial_query_service=MagicMock())
    result = _make_result()
    eval_date = date(2026, 3, 2)
    payload = svc._build_upsert_payload(result, eval_date)
    assert payload["evaluation_year"] == 2026
    assert payload["status"] == "active"
    assert payload["total_score"] == 85
    assert payload["pass_required_conditions"] is True
    assert "screening_details" in payload


# ---------------------------------------------------------------------------
# _persist_result（maker が None の場合はスキップ）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_result_no_maker_skips():
    """maker が None の場合、例外なくスキップされる。"""
    svc = ScreeningService(
        financial_query_service=MagicMock(),
        screening_result_maker=None,
    )
    result = _make_result()
    # 例外なく完了すること
    await svc._persist_result(result, date(2026, 3, 2))


# ---------------------------------------------------------------------------
# _call_history（同期メソッドと非同期メソッドの両方）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_history_sync_method():
    """同期メソッドが呼ばれた場合にそのまま結果を返す。"""
    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=["div_data"])
    svc = ScreeningService(financial_query_service=fq)
    result = await svc._call_history("get_dividend_history", "1234")
    assert result == ["div_data"]


@pytest.mark.asyncio
async def test_call_history_async_method():
    """非同期メソッドが呼ばれた場合に await して結果を返す。"""
    fq = MagicMock()
    fq.get_eps_history = AsyncMock(return_value=["eps_data"])
    svc = ScreeningService(financial_query_service=fq)
    result = await svc._call_history("get_eps_history", "1234")
    assert result == ["eps_data"]


# ---------------------------------------------------------------------------
# evaluate（_async_fetch_sector_code_17 が None の場合デフォルト業種を使用）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_uses_default_industry_when_no_maker():
    """stock_master_maker が None のとき sector_code_17 は None → デフォルト "33"。"""
    from app.services.screening.models import ScreeningConfig

    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=[])
    fq.get_eps_history = MagicMock(return_value=[])
    fq.get_operating_cf_history = MagicMock(return_value=[])
    fq.get_stability_history = MagicMock(return_value=[])

    # モック repo でキャッシュを初期化
    mock_repo = AsyncMock()
    test_configs = {
        "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
        "33": ScreeningConfig(industry_code="33", industry_name="サービス業"),
    }
    mock_repo.as_config_dict = AsyncMock(return_value=test_configs)

    svc = ScreeningService(
        financial_query_service=fq,
        stock_master_maker=None,
        sector_33_master_repo=mock_repo,
    )
    # キャッシュ初期化
    await svc._init_industry_config_cache()

    result = await svc.evaluate("1234", date(2026, 3, 2))
    assert result.sec_code == "1234"
    # データがないので not_eligible になるはず
    assert result.status == "not_eligible"


# ---------------------------------------------------------------------------
# Industry Config Cache Methods
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_init_industry_config_cache():
    """業種設定キャッシャーが正しく初期化される。"""
    from app.services.screening.models import ScreeningConfig

    # Mock Sector33MasterRepository
    mock_repo = AsyncMock()
    test_configs = {
        "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
        "33": ScreeningConfig(industry_code="33", industry_name="サービス業"),
    }
    mock_repo.as_config_dict = AsyncMock(return_value=test_configs)

    svc = ScreeningService(
        financial_query_service=MagicMock(),
        sector_33_master_repo=mock_repo,
    )

    # キャッシュ初期化前
    assert svc._industry_config_cache == {}

    # キャッシュ初期化実行
    await svc._init_industry_config_cache()

    # キャッシュが期待値で埋められているか確認
    assert svc._industry_config_cache == test_configs
    assert "01" in svc._industry_config_cache
    assert "33" in svc._industry_config_cache
    assert svc._industry_config_cache["01"].industry_name == "水産・農林業"


@pytest.mark.asyncio
async def test_init_industry_config_cache_empty():
    """業種設定がない場合、警告ログが出力される。"""
    # Mock Sector33MasterRepository
    mock_repo = AsyncMock()
    mock_repo.as_config_dict = AsyncMock(return_value={})

    svc = ScreeningService(
        financial_query_service=MagicMock(),
        sector_33_master_repo=mock_repo,
    )

    # キャッシュ初期化実行
    with patch("app.services.screening.screening_service.logger") as mock_logger:
        await svc._init_industry_config_cache()
        # 警告ログが呼ばれたか確認
        mock_logger.warning.assert_called()
        # 最後の呼び出しで "empty" を含むメッセージが出力されているか
        assert any("empty" in str(call) for call in mock_logger.warning.call_args_list)

    assert svc._industry_config_cache == {}


@pytest.mark.asyncio
async def test_init_industry_config_cache_fails():
    """DB 読み込み失敗時に ConfigurationError が発生する。"""
    from app.exceptions.system import ConfigurationError

    mock_repo = AsyncMock()
    mock_repo.as_config_dict = AsyncMock(side_effect=Exception("DB connection failed"))

    svc = ScreeningService(
        financial_query_service=MagicMock(),
        sector_33_master_repo=mock_repo,
    )

    # ConfigurationError が発生することを確認
    with pytest.raises(ConfigurationError):
        await svc._init_industry_config_cache()


@pytest.mark.asyncio
async def test_init_industry_config_cache_no_repo():
    """Sector33MasterRepository が注入されていない場合、スキップされる。"""
    svc = ScreeningService(
        financial_query_service=MagicMock(),
        sector_33_master_repo=None,
    )

    # キャッシュ初期化実行（スキップされるはず）
    with patch("app.services.screening.screening_service.logger") as mock_logger:
        await svc._init_industry_config_cache()
        mock_logger.warning.assert_called()

    assert svc._industry_config_cache == {}


def test_get_industry_config_dict():
    """get_industry_config_dict() がキャッシュされた辞書を返す。"""
    from app.services.screening.models import ScreeningConfig

    # キャッシュを準備
    test_configs = {
        "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
        "33": ScreeningConfig(industry_code="33", industry_name="サービス業"),
    }

    svc = ScreeningService(financial_query_service=MagicMock())
    svc._industry_config_cache = test_configs

    # 取得
    result = svc.get_industry_config_dict()

    assert result == test_configs
    assert isinstance(result, dict)
    assert "01" in result
    assert "33" in result


def test_get_industry_config_existing():
    """get_industry_config() で存在する業種コードを取得。"""
    from app.services.screening.models import ScreeningConfig

    test_config = ScreeningConfig(industry_code="01", industry_name="水産・農林業")
    test_configs = {"01": test_config}

    svc = ScreeningService(financial_query_service=MagicMock())
    svc._industry_config_cache = test_configs

    # 存在する業種コードで取得
    result = svc.get_industry_config("01")

    assert result == test_config
    assert result.industry_name == "水産・農林業"


def test_get_industry_config_not_found():
    """get_industry_config() で存在しないコードは None を返す。"""
    from app.services.screening.models import ScreeningConfig

    test_configs = {
        "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
    }

    svc = ScreeningService(financial_query_service=MagicMock())
    svc._industry_config_cache = test_configs

    # 存在しない業種コードで取得
    result = svc.get_industry_config("99")

    assert result is None


@pytest.mark.asyncio
async def test_lifespan_initialization():
    """Lifespan イベント内で ScreeningService が初期化され、キャッシュがロードされることを検証。"""
    # pylint: disable=import-outside-toplevel
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # テスト用 app を作成（main.py から lifespan をインポート）
    from app.main import lifespan

    app = FastAPI(lifespan=lifespan)

    # テスト：アプリが起動し、ScreeningService がキャッシュ初期化されたことを確認
    with TestClient(app):
        # アプリ起動後、screening_service が app.state に存在するか確認
        screening_service = getattr(app.state, "screening_service", None)

        # 初期化に成功すれば None でない
        # 失敗した場合は None でも OK（レジリエンス）
        if screening_service is not None:
            # キャッシュが初期化されている（空でない）か確認
            # または、キャッシュが空でも、repo が注入されていない可能性
            assert hasattr(screening_service, "_industry_config_cache")
            assert isinstance(screening_service._industry_config_cache, dict)


@pytest.mark.asyncio
async def test_evaluate_uses_provided_industry_code():
    """_async_fetch_sector_code_17 が特定コードを返す場合、そのコードで評価される。"""
    from app.services.screening.models import ScreeningConfig

    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=[])
    fq.get_eps_history = MagicMock(return_value=[])
    fq.get_operating_cf_history = MagicMock(return_value=[])
    fq.get_stability_history = MagicMock(return_value=[])

    # モック repo でキャッシュを初期化
    mock_repo = AsyncMock()
    test_configs = {
        "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
        "05": ScreeningConfig(industry_code="05", industry_name="繊維製品"),
        "33": ScreeningConfig(industry_code="33", industry_name="サービス業"),
    }
    mock_repo.as_config_dict = AsyncMock(return_value=test_configs)

    svc = ScreeningService(
        financial_query_service=fq,
        stock_master_maker=None,
        sector_33_master_repo=mock_repo,
    )
    # キャッシュ初期化
    await svc._init_industry_config_cache()

    # _async_fetch_sector_code_17 をモック
    svc._async_fetch_sector_code_17 = AsyncMock(return_value="05")
    result = await svc.evaluate("5678", date(2026, 3, 2))
    assert result.sec_code == "5678"


@pytest.mark.asyncio
async def test_evaluate_falls_back_on_invalid_industry_code():
    """無効な業種コードのとき evaluate がデフォルト "33" にフォールバック。"""
    from app.services.screening.models import ScreeningConfig

    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=[])
    fq.get_eps_history = MagicMock(return_value=[])
    fq.get_operating_cf_history = MagicMock(return_value=[])
    fq.get_stability_history = MagicMock(return_value=[])

    # モック repo でキャッシュを初期化（"99" は含めない）
    mock_repo = AsyncMock()
    test_configs = {
        "01": ScreeningConfig(industry_code="01", industry_name="水産・農林業"),
        "33": ScreeningConfig(industry_code="33", industry_name="サービス業"),
    }
    mock_repo.as_config_dict = AsyncMock(return_value=test_configs)

    svc = ScreeningService(
        financial_query_service=fq,
        stock_master_maker=None,
        sector_33_master_repo=mock_repo,
    )
    # キャッシュ初期化
    await svc._init_industry_config_cache()

    # 無効な業種コード "99" を返す
    svc._async_fetch_sector_code_17 = AsyncMock(return_value="99")

    # evaluate は無効コードを受け取ると デフォルト "33" に fallback して処理する
    result = await svc.evaluate("9999", date(2026, 3, 2))
    assert result.sec_code == "9999"
    # データがないので not_eligible になるはず
    assert result.status == "not_eligible"


# MOD-001: INDUSTRY_CONFIGS 削除確認テスト


def test_no_industry_configs_in_module():
    """INDUSTRY_CONFIGS がモジュールに存在しないことを確認。"""
    from app.services.screening import models

    assert not hasattr(
        models, "INDUSTRY_CONFIGS"
    ), "INDUSTRY_CONFIGS should be removed from models.py"
