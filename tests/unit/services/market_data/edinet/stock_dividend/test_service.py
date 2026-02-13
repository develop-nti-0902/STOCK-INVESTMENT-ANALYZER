"""Unit tests for EdinetStockDividendService."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.services.market_data.edinet.stock_dividend.service import EdinetStockDividendService


@pytest.mark.asyncio
async def test_get_latest_and_by_period_and_annual_and_multiple_latest():
    """各種取得メソッド（最新・期間・年度・複数取得）が期待通りに動作することを検証する."""

    # prepare saver with async methods and repository
    async def fake_get_latest(sec_code: str):
        return {"sec_code": sec_code, "value": "latest"}

    async def fake_find_by_period(sec_code: str, period_end_date: date):
        return {"sec_code": sec_code, "period_end_date": period_end_date}

    async def fake_find_by_fiscal_year(sec_code: str, fiscal_year: int):
        return {"sec_code": sec_code, "fiscal_year": fiscal_year}

    async def fake_get_latest_by_sec_codes(sec_codes: list[str]):
        return [{"sec_code": s} for s in sec_codes]

    repository = SimpleNamespace(
        find_by_period=fake_find_by_period,
        find_by_fiscal_year=fake_find_by_fiscal_year,
        get_latest_by_sec_codes=fake_get_latest_by_sec_codes,
    )

    saver = SimpleNamespace(
        get_latest_by_sec_code=fake_get_latest,
        repository=repository,
        save_single=lambda *a, **k: None,
    )
    parser = SimpleNamespace(parse_root=lambda *a, **k: None)
    converter = SimpleNamespace()
    file_manager = SimpleNamespace()
    download_service = SimpleNamespace()

    service = EdinetStockDividendService(parser, converter, saver, file_manager, download_service)

    latest = await service.get_latest_data("7203")
    assert latest["sec_code"] == "7203"

    period = date(2024, 3, 31)
    by_period = await service.get_by_period("7203", period)
    assert by_period["period_end_date"] == period

    annual = await service.get_annual_data("7203", 2023)
    assert annual["fiscal_year"] == 2023

    multiples = await service.get_multiple_latest(["7203", "6758"])
    assert isinstance(multiples, list) and len(multiples) == 2


@pytest.mark.asyncio
async def test_cleanup_old_files_no_work_dir_returns_zero():
    """作業ディレクトリが無ければクリーンアップは0を返すことを確認する."""
    parser = SimpleNamespace(parse_root=lambda *a, **k: None)
    converter = SimpleNamespace()
    saver = SimpleNamespace(
        get_latest_by_sec_code=lambda *a, **k: None,
        save_single=lambda *a, **k: None,
        repository=SimpleNamespace(),
    )
    file_manager = SimpleNamespace()
    download_service = SimpleNamespace(work_dir=None)

    service = EdinetStockDividendService(parser, converter, saver, file_manager, download_service)
    result = await service.cleanup_old_files()
    assert result == 0


@pytest.mark.asyncio
async def test_cleanup_old_files_with_work_dir_calls_file_manager():
    """作業ディレクトリがある場合に file_manager が呼ばれることを確認する."""
    parser = SimpleNamespace(parse_root=lambda *a, **k: None)
    converter = SimpleNamespace()
    saver = SimpleNamespace(
        get_latest_by_sec_code=lambda *a, **k: None,
        save_single=lambda *a, **k: None,
        repository=SimpleNamespace(),
    )

    # file_manager.cleanup_old_files is synchronous and should return int
    def fake_cleanup(work_dir: str, max_age_hours: int = 24):
        assert work_dir == "./tmp"
        assert max_age_hours == 12
        return 7

    file_manager = SimpleNamespace(cleanup_old_files=fake_cleanup)
    download_service = SimpleNamespace(work_dir="./tmp")

    service = EdinetStockDividendService(parser, converter, saver, file_manager, download_service)
    result = await service.cleanup_old_files(max_age_hours=12)
    assert result == 7
