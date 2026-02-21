"""`DividendYieldMonitoringService` のユニットテスト."""

from datetime import date, datetime
from decimal import Decimal
from types import MethodType, SimpleNamespace

import pytest

from app.services.monitoring.dividend_yield_monitoring_service import (
    DividendYieldMonitoringResult,
    DividendYieldMonitoringService,
)


class DummyMaker:
    """簡易セッションコンテキストを提供するダミーオブジェクト。"""

    def __init__(self, session):
        """セッションオブジェクトを保持するだけの初期化。"""
        self._session = session

    def __call__(self):
        """セッションコンテキストを返す。"""
        return self

    async def __aenter__(self):
        """コンテキストマネージャーの Enter 処理。"""
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        """コンテキストマネージャーの Exit 処理。"""
        return False


class MockEdinetRepository:
    """特定レコードを返すダミー配当リポジトリ。"""

    def __init__(self, record: SimpleNamespace):
        """返却レコードを保持する。"""
        self._record = record

    async def find_latest_by_sec_code(self, sec_code: str):
        """指定コードと一致するレコードを返す。"""
        if self._record is None or getattr(self._record, "sec_code", None) != sec_code:
            return None
        return self._record


class MockStockRepository:
    """最新株価を返すダミー株価リポジトリ。"""

    def __init__(self, record: SimpleNamespace):
        """返却レコードを保持する。"""
        self._record = record

    async def get_latest(self, symbol: str, limit: int = 1):
        """指定シンボルの最新データを返す。"""
        if self._record is None or getattr(self._record, "symbol", None) != symbol:
            return []
        return [self._record]


@pytest.mark.asyncio
async def test_calculate_for_stock_prioritizes_high_yield():
    """高利回り銘柄が priority レベルになることを確認する。"""
    session = object()
    builder = DummyMaker(session)
    dividend_record = SimpleNamespace(
        sec_code="7203",
        dividend_actual=Decimal("63"),
        period_end_date=date(2025, 3, 31),
    )
    stock_record = SimpleNamespace(
        symbol="7203",
        close=Decimal("1500"),
        timestamp=datetime(2026, 2, 21, 0, 0),
    )

    service = DividendYieldMonitoringService(
        session_maker=builder,
        edinet_repo_factory=lambda session: MockEdinetRepository(dividend_record),
        stock_repo_factory=lambda session: MockStockRepository(stock_record),
    )
    service._screening_index["7203"] = SimpleNamespace(
        sec_code="7203",
        status="watch",
        total_score=85,
        fiscal_year_end=date(2025, 3, 31),
    )

    result = await service.calculate_for_stock("7203", date(2026, 2, 21))

    assert result.purchase_level == "priority"
    assert result.dividend_amount == Decimal("63")
    assert result.stock_price == Decimal("1500")
    assert result.dividend_yield.quantize(Decimal("0.1")) == Decimal("4.2")
    assert result.screening_status == "watch"
    assert result.screening_score == 85
    assert result.dividend_fiscal_year_end == date(2025, 3, 31)
    assert result.stock_price_date == date(2026, 2, 21)


@pytest.mark.asyncio
async def test_run_groups_results_and_prints_summary(capsys):
    """run() が各グループと永続化を呼ぶことを検証する。"""
    session = object()
    builder = DummyMaker(session)
    service = DividendYieldMonitoringService(session_maker=builder)

    async def fake_fetch(self):
        return [
            SimpleNamespace(
                sec_code="7203", status="priority", total_score=85, fiscal_year_end=None
            ),
            SimpleNamespace(sec_code="6758", status="active", total_score=72, fiscal_year_end=None),
            SimpleNamespace(sec_code="9998", status="watch", total_score=60, fiscal_year_end=None),
        ]

    service._fetch_screening_results = MethodType(fake_fetch, service)

    monitoring_map = {
        "7203": DividendYieldMonitoringResult(
            sec_code="7203",
            dividend_amount=Decimal("63"),
            stock_price=Decimal("1500"),
            dividend_yield=Decimal("4.2"),
            purchase_level="priority",
            screening_status="priority",
            screening_score=85,
            stock_price_date=date(2026, 2, 21),
            dividend_fiscal_year_end=date(2025, 3, 31),
        ),
        "6758": DividendYieldMonitoringResult(
            sec_code="6758",
            dividend_amount=Decimal("40"),
            stock_price=Decimal("1100"),
            dividend_yield=Decimal("3.6"),
            purchase_level="consider",
            screening_status="active",
            screening_score=72,
            stock_price_date=date(2026, 2, 21),
            dividend_fiscal_year_end=date(2025, 3, 31),
        ),
        "9998": DividendYieldMonitoringResult(
            sec_code="9998",
            dividend_amount=None,
            stock_price=None,
            dividend_yield=None,
            purchase_level="unavailable",
            screening_status="watch",
            screening_score=60,
            stock_price_date=None,
            dividend_fiscal_year_end=None,
            error_message="配当データなし",
        ),
    }

    async def fake_calculate(self, sec_code, monitoring_date):
        return monitoring_map[sec_code]

    service.calculate_for_stock = MethodType(fake_calculate, service)

    persisted_calls: list[tuple[date, list[DividendYieldMonitoringResult]]] = []

    async def fake_persist(self, monitoring_date, monitoring_results):
        persisted_calls.append((monitoring_date, monitoring_results))

    service._persist_monitoring_results = MethodType(fake_persist, service)

    await service.run(date(2026, 2, 21))

    captured = capsys.readouterr()
    assert "優先購入候補" in captured.out
    assert "購入検討" in captured.out
    assert "データ取得不可" in captured.out
    assert "合計監視対象: 3銘柄 / 優先購入候補: 1銘柄 / 購入検討: 1銘柄" in captured.out
    assert len(persisted_calls) == 1
    saved_date, saved_results = persisted_calls[0]
    assert saved_date == date(2026, 2, 21)
    assert {entry.sec_code for entry in saved_results} == {"7203", "6758", "9998"}
