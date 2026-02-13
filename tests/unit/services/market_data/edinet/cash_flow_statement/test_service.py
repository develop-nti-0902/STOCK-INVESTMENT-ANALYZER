"""Tests for EdinetCashFlowStatementService."""

from __future__ import annotations

import pytest

from app.services.market_data.edinet.edinet_cash_flow_statement.service import (
    EdinetCashFlowStatementService,
)


@pytest.mark.asyncio
async def test_get_latest_by_sec_code_delegation():
    """get_latest_by_sec_code がリポジトリのメソッドを正しく呼び出すことを検証する."""

    class FakeRepo:
        async def find_latest_by_sec_code(self, sec_code: str):
            return {"sec_code": sec_code, "value": 1}

    class FakeSaver:
        def __init__(self):
            self.repository = FakeRepo()

    svc = EdinetCashFlowStatementService(
        parser=object(),
        converter=object(),
        saver=FakeSaver(),
        file_manager=object(),
        download_service=object(),
    )

    res = await svc.get_latest_by_sec_code("7203")
    assert isinstance(res, dict)
    assert res["sec_code"] == "7203"
