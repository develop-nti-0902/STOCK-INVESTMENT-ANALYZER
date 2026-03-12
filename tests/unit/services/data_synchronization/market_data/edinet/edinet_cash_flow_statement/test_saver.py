"""Tests for EdinetCashFlowStatementSaver."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.data_synchronization.market_data.edinet.edinet_cash_flow_statement.saver import (
    EdinetCashFlowStatementSaver,
)


class FakeRepo:
    """シンプルなフェイクリポジトリ（テスト用)."""

    def __init__(self):
        """内部ストアを初期化する."""
        self.upserts = []

    async def upsert(self, data):
        """データを記録して模擬的に保存結果を返す."""
        self.upserts.append(data)
        return {"saved": data}


@pytest.mark.asyncio
async def test_validate_data_and_save_batch():
    """Saver のバリデーションとバッチ保存フローを確認する."""
    saver = EdinetCashFlowStatementSaver(session=object())
    saver.repository = FakeRepo()

    good = {
        "doc_id": "S100N8ST",
        "sec_code": "7203",
        "submission_date": date(2024, 4, 1),
        "period_end_date": date(2024, 3, 31),
        "report_type": "annual",
    }

    assert await saver.validate_data(good)

    data_list = [good, good]
    saved_count = await saver.save_batch(data_list)
    assert saved_count == 2
    assert len(saver.repository.upserts) == 2
