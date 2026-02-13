"""`StockMasterSaver` の単体テスト.

テスト内容:
 - 空のレコードリストで 0 を返すこと
 - チャンクごとの `bulk_upsert` の戻り値を合算して返すこと
 - `bulk_upsert` が `None` を返した場合は 0 として扱うこと
 - メソッド呼び出し時の `batch_size` オーバーライドが効くこと
"""

import asyncio
from typing import Callable, Optional

from app.services.market_data.stock_master.saver import StockMasterSaver


class DummyRepo:
    """ダミーのリポジトリ実装 for tests."""

    def __init__(self, return_val: Optional[Callable] = None):
        """初期化.

        `return_val` はチャンクを受け取る callable(chunk) -> int|None か、静的な値のいずれか.
        """
        # return_val はチャンクを受け取る callable(chunk) -> int|None か、静的な値のいずれか
        self.return_val = return_val
        self.calls = []

    async def bulk_upsert(self, chunk):
        """チャンクを受け取り、事前定義の戻り値を返す."""
        self.calls.append(list(chunk))
        if callable(self.return_val):
            return self.return_val(chunk)
        return self.return_val


def test_save_batch_returns_zero_for_empty_records():
    """空のレコードリストで 0 が返ることを確認する."""
    repo = DummyRepo(return_val=lambda c: len(c))
    saver = StockMasterSaver(repo=repo, batch_size=10)

    result = asyncio.run(saver.save_batch([]))

    assert result == 0
    assert repo.calls == []


def test_save_batch_accumulates_counts_per_chunk():
    """チャンクごとの合計件数が正しく算出されることを確認する."""
    # リポジトリはチャンクごとに処理した件数を返す想定
    repo = DummyRepo(return_val=lambda c: len(c))
    saver = StockMasterSaver(repo=repo, batch_size=2)

    records = [{"stock_code": str(i)} for i in range(5)]
    total = asyncio.run(saver.save_batch(records))

    assert total == 5
    # 呼ばれたチャンクは 3 回: 2,2,1
    assert [len(c) for c in repo.calls] == [2, 2, 1]


def test_save_batch_handles_none_returned_by_repo():
    """リポジトリが None を返した場合 0 と扱われることを確認する."""
    # リポジトリが None を返す場合は 0 として扱う
    repo = DummyRepo(return_val=None)
    saver = StockMasterSaver(repo=repo, batch_size=3)

    records = [{"stock_code": "1"}, {"stock_code": "2"}]
    total = asyncio.run(saver.save_batch(records))

    assert total == 0
    assert len(repo.calls) == 1


def test_save_batch_respects_override_batch_size():
    """batch_size の上書きが反映されることを確認する."""
    # デフォルトの batch_size は 5 だが、この呼び出しでは 2 にオーバーライドする
    repo = DummyRepo(return_val=lambda c: len(c))
    saver = StockMasterSaver(repo=repo, batch_size=5)

    records = [{"stock_code": str(i)} for i in range(4)]
    total = asyncio.run(saver.save_batch(records, batch_size=2))

    assert total == 4
    assert [len(c) for c in repo.calls] == [2, 2]
