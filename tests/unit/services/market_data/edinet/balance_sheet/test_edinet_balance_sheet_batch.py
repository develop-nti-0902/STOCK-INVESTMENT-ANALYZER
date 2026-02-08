"""`EdinetBalanceSheetBatchRunner` の単体テスト.

範囲:
- 日次検索ループのフィルタリング動作
- 引数バリデーション（start_date/end_date）
- ドキュメント0件時の戻り値

テスト規約に従い、外部依存はモック化して短く保っています。
"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.market_data.edinet.balance_sheet.batch import EdinetBalanceSheetBatchRunner


def _make_runner(fetcher=None):
    # コンストラクタは AsyncSession を必須とするため、テスト用の AsyncMock を注入する
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    runner = EdinetBalanceSheetBatchRunner(
        batch_service=object(),
        fetcher=fetcher or object(),
        parser=object(),
        file_manager=object(),
        session=session,
    )
    return runner


def test_search_documents_filters_and_aggregates_across_days():
    """日次ループが正しくフィルタリングして集約することを確認する."""
    # 準備: 日ごとに返すドキュメントを設定
    docs_day1 = [
        {"docTypeCode": "120", "secCode": "1234", "docDescription": "", "docID": "d1"},
        {"docTypeCode": "120", "secCode": None, "docDescription": "", "docID": "d2"},
        {"docTypeCode": "119", "secCode": "5678", "docDescription": "", "docID": "d3"},
        {
            "docTypeCode": "120",
            "secCode": "999",
            "docDescription": "受益証券 レポート",
            "docID": "d4",
        },
    ]

    docs_day2 = [{"docTypeCode": "120", "secCode": "2222", "docDescription": "", "docID": "d5"}]

    fetcher = MagicMock()
    fetcher.search_documents = AsyncMock(side_effect=[docs_day1, docs_day2])

    runner = _make_runner(fetcher=fetcher)

    start = date(2025, 12, 1)
    end = date(2025, 12, 2)

    result = asyncio.run(runner._search_documents(start, end))

    # d1 と d5 のみが条件を満たす
    ids = {d["docID"] for d in result}
    assert ids == {"d1", "d5"}
    assert len(result) == 2


def test_fetch_balance_sheets_missing_dates_raises():
    """start_date / end_date が指定されない場合は ValueError を投げる."""
    runner = _make_runner()

    with pytest.raises(ValueError):
        asyncio.run(runner.fetch_balance_sheets(start_date=None, end_date=None))


def test_fetch_balance_sheets_returns_zero_on_no_documents():
    """検索結果が0件の場合、統計が0の辞書を返すことを確認する."""
    fetcher = MagicMock()
    runner = _make_runner(fetcher=fetcher)

    # _search_documents を空リストにする
    with patch.object(runner, "_search_documents", new=AsyncMock(return_value=[])):
        # BatchExecutionContext をモック化して安全に通過させる
        fake_ctx = AsyncMock()
        fake_ctx.__aenter__.return_value = AsyncMock()
        fake_ctx.__aexit__.return_value = AsyncMock()

        with patch(
            "app.services.market_data.edinet.balance_sheet.batch.BatchExecutionContext",
            return_value=fake_ctx,
        ):
            res = asyncio.run(
                runner.fetch_balance_sheets(start_date=date(2025, 1, 1), end_date=date(2025, 1, 1))
            )

    assert res["total_documents"] == 0
    assert res["processed_documents"] == 0
    assert res["saved_years"] == 0
