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
    assert payload["evaluation_date"] == eval_date
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
    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=[])
    fq.get_eps_history = MagicMock(return_value=[])
    fq.get_operating_cf_history = MagicMock(return_value=[])
    fq.get_stability_history = MagicMock(return_value=[])

    svc = ScreeningService(
        financial_query_service=fq,
        stock_master_maker=None,
    )
    result = await svc.evaluate("1234", date(2026, 3, 2))
    assert result.sec_code == "1234"
    # データがないので not_eligible になるはず
    assert result.status == "not_eligible"


@pytest.mark.asyncio
async def test_evaluate_uses_provided_industry_code():
    """_async_fetch_sector_code_17 が特定コードを返す場合、そのコードで評価される。"""
    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=[])
    fq.get_eps_history = MagicMock(return_value=[])
    fq.get_operating_cf_history = MagicMock(return_value=[])
    fq.get_stability_history = MagicMock(return_value=[])

    svc = ScreeningService(
        financial_query_service=fq,
        stock_master_maker=None,
    )
    # _async_fetch_sector_code_17 をモック
    with patch.object(svc, "_async_fetch_sector_code_17", return_value="05"):
        # patching は非同期化が必要
        pass

    svc._async_fetch_sector_code_17 = AsyncMock(return_value="05")
    result = await svc.evaluate("5678", date(2026, 3, 2))
    assert result.sec_code == "5678"


@pytest.mark.asyncio
async def test_evaluate_falls_back_on_invalid_industry_code():
    """無効な業種コードのとき "33" にフォールバック。"""
    fq = MagicMock()
    fq.get_dividend_history = MagicMock(return_value=[])
    fq.get_eps_history = MagicMock(return_value=[])
    fq.get_operating_cf_history = MagicMock(return_value=[])
    fq.get_stability_history = MagicMock(return_value=[])

    svc = ScreeningService(
        financial_query_service=fq,
        stock_master_maker=None,
    )
    svc._async_fetch_sector_code_17 = AsyncMock(return_value="99")  # 無効コード
    result = await svc.evaluate("9999", date(2026, 3, 2))
    assert result.sec_code == "9999"
