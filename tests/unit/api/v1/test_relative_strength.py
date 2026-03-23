"""Unit tests for `app.api.v1.relative_strength` endpoints."""

from datetime import date, timedelta

import pytest

from app.api.v1 import relative_strength as rs_mod
from app.services.data_synchronization.market_data.relative_strength import (
    RelativeStrengthAllResult,
    RelativeStrengthResult,
)


class DummyRelativeStrengthService:
    """シンプルなモックサービス実装 (テスト用)."""

    def __init__(self, *, calculate_for_date_result=None, calculate_all_result=None):
        """初期化."""
        self._calculate_for_date_result = calculate_for_date_result
        self._calculate_all_result = calculate_all_result

    async def calculate_for_date(self, target_date):
        """calculate_for_date のモック実装."""
        if self._calculate_for_date_result is None:
            return RelativeStrengthResult(
                rowcount=10,
                skipped_count=2,
                error_count=0,
                calculation_date=target_date,
                message="Completed: 10 upserted, 2 skipped, 0 errors",
            )
        return self._calculate_for_date_result

    async def calculate_all(self):
        """calculate_all のモック実装."""
        if self._calculate_all_result is None:
            return RelativeStrengthAllResult(
                total_symbols=100,
                total_rowcount=1000,
                error_count=0,
                message="Completed: 1000 upserted, 100 symbols, 0 errors",
            )
        return self._calculate_all_result


@pytest.mark.asyncio
async def test_calculate_relative_strength_for_date_returns_completed_status():
    """指定日付のRS計算が成功し、completed ステータスが返ることを検証する."""
    today = date.today()
    svc = DummyRelativeStrengthService()

    resp = await rs_mod.calculate_relative_strength_for_date(
        request=rs_mod.CalculateRelativeStrengthRequest(target_date=today),
        service=svc,
    )

    assert resp.status == "completed"
    assert resp.calculation_date == today.isoformat()
    assert resp.rowcount == 10
    assert resp.skipped_count == 2
    assert resp.error_count == 0


@pytest.mark.asyncio
async def test_calculate_relative_strength_for_date_handles_partial_error():
    """エラーが存在する場合、partial_error ステータスが返ることを検証する."""
    today = date.today()
    result = RelativeStrengthResult(
        rowcount=8,
        skipped_count=2,
        error_count=2,
        calculation_date=today,
        message="Partial error occurred",
    )
    svc = DummyRelativeStrengthService(calculate_for_date_result=result)

    resp = await rs_mod.calculate_relative_strength_for_date(
        request=rs_mod.CalculateRelativeStrengthRequest(target_date=today),
        service=svc,
    )

    assert resp.status == "partial_error"
    assert resp.error_count == 2


@pytest.mark.asyncio
async def test_calculate_relative_strength_for_date_handles_no_data():
    """データがない場合、no_data ステータスが返ることを検証する."""
    today = date.today()
    result = RelativeStrengthResult(
        rowcount=0,
        skipped_count=0,
        error_count=0,
        calculation_date=today,
        message="No data available",
    )
    svc = DummyRelativeStrengthService(calculate_for_date_result=result)

    resp = await rs_mod.calculate_relative_strength_for_date(
        request=rs_mod.CalculateRelativeStrengthRequest(target_date=today),
        service=svc,
    )

    assert resp.status == "no_data"
    assert resp.rowcount == 0


@pytest.mark.asyncio
async def test_calculate_relative_strength_for_date_rejects_future_date():
    """未来日付のリクエストが拒否されることを検証する."""
    from fastapi import HTTPException

    tomorrow = date.today() + timedelta(days=1)
    svc = DummyRelativeStrengthService()

    with pytest.raises(HTTPException) as exc_info:
        await rs_mod.calculate_relative_strength_for_date(
            request=rs_mod.CalculateRelativeStrengthRequest(target_date=tomorrow),
            service=svc,
        )

    assert exc_info.value.status_code == 400
    assert "future date" in exc_info.value.detail


@pytest.mark.asyncio
async def test_calculate_relative_strength_all_returns_completed_status():
    """全期間のRS計算が成功し、completed ステータスが返ることを検証する."""
    svc = DummyRelativeStrengthService()

    resp = await rs_mod.calculate_relative_strength_all(service=svc)

    assert resp.status == "completed"
    assert resp.total_symbols == 100
    assert resp.total_rowcount == 1000
    assert resp.error_count == 0


@pytest.mark.asyncio
async def test_calculate_relative_strength_all_handles_partial_error():
    """エラーが存在する場合、partial_error ステータスが返ることを検証する."""
    result = RelativeStrengthAllResult(
        total_symbols=100,
        total_rowcount=900,
        error_count=5,
        message="Partial error occurred",
    )
    svc = DummyRelativeStrengthService(calculate_all_result=result)

    resp = await rs_mod.calculate_relative_strength_all(service=svc)

    assert resp.status == "partial_error"
    assert resp.error_count == 5


@pytest.mark.asyncio
async def test_calculate_relative_strength_for_date_wraps_service_exception():
    """サービス側の例外が HTTPException にラップされることを検証する."""
    from fastapi import HTTPException

    class BadService(DummyRelativeStrengthService):
        async def calculate_for_date(self, target_date):
            raise RuntimeError("Database connection failed")

    today = date.today()
    svc = BadService()

    with pytest.raises(HTTPException) as exc_info:
        await rs_mod.calculate_relative_strength_for_date(
            request=rs_mod.CalculateRelativeStrengthRequest(target_date=today),
            service=svc,
        )

    assert exc_info.value.status_code == 500
    assert "Unexpected error" in exc_info.value.detail


@pytest.mark.asyncio
async def test_calculate_relative_strength_all_wraps_service_exception():
    """サービス側の例外が HTTPException にラップされることを検証する."""
    from fastapi import HTTPException

    class BadService(DummyRelativeStrengthService):
        async def calculate_all(self):
            raise RuntimeError("Database connection failed")

    svc = BadService()

    with pytest.raises(HTTPException) as exc_info:
        await rs_mod.calculate_relative_strength_all(service=svc)

    assert exc_info.value.status_code == 500
    assert "Unexpected error" in exc_info.value.detail
