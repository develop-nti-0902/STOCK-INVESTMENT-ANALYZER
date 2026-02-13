"""Tests for EdinetCashFlowStatementSaver."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.market_data.edinet.edinet_cash_flow_statement.saver import (
    EdinetCashFlowStatementSaver,
)


class FakeRepo:
    """テスト用の簡易リポジトリモック."""

    def __init__(self):
        """初期化."""
        self.upserts = []

    async def upsert(self, data):
        """渡されたデータを記録して模擬保存結果を返す."""
        self.upserts.append(data)
        return {"saved": data}


@pytest.mark.asyncio
async def test_validate_data_and_save_batch():
    """validate_data と save_batch の基本動作を検証する."""
    saver = EdinetCashFlowStatementSaver(session=object())
    # inject fake repository to avoid DB
    saver.repository = FakeRepo()

    good = {
        "doc_id": "S100N8ST",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "report_type": "annual",
    }

    assert await saver.validate_data(good)

    # batch save
    data_list = [good, good]
    saved_count = await saver.save_batch(data_list)
    assert saved_count == 2
    assert len(saver.repository.upserts) == 2
