"""
`app.api.v1.batch` のユニットテスト（バッチ管理APIに合わせて再作成）。

このファイルは管理用エンドポイント `get_job_status`、`get_history`、
および `cancel_job` の振る舞いと、内部ユーティリティ `_job_to_response_dict` の
出力正規化を検証します。

テストは AAA パターンに従い、日本語の説明を含めます。
"""

from types import SimpleNamespace

import pytest

from app.api.v1 import batch as batch_module
from app.exceptions.database import RecordNotFoundError


class DummyJob:
    """ダミーのジョブオブジェクト。

    任意の属性をコンストラクタで受け取り、`_job_to_response_dict` の
    期待する属性を簡単に模倣できるようにする。
    """

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DummyRepo:
    """`BatchExecutionRepository` の最小限のモック実装。"""

    def __init__(self, get_result=None, by_type=None, recent=None, cancel_result=None):
        self._get = get_result
        self._by_type = by_type or []
        self._recent = recent or []
        self._cancel = cancel_result

    async def get(self, job_id: int):
        return self._get

    async def get_by_job_type(self, job_type: str):
        return self._by_type

    async def get_recent(self, limit: int = 10):
        return self._recent

    async def cancel_job(self, job_id: int):
        return self._cancel


@pytest.mark.asyncio
async def test_get_job_status_not_found_raises():
    """ジョブが存在しない場合は `RecordNotFoundError` を返すこと。"""
    repo = DummyRepo(get_result=None)
    with pytest.raises(RecordNotFoundError):
        await batch_module.get_job_status(1, repo=repo)


@pytest.mark.asyncio
async def test_get_job_status_returns_job():
    """存在するジョブは `BatchExecutionResponse` として返されること。"""
    job = DummyJob(id=7, status="PENDING", batch_type="JPX_ALL_STOCKS", total_stocks=0)
    repo = DummyRepo(get_result=job)

    resp = await batch_module.get_job_status(7, repo=repo)
    assert resp.job_id == "7"
    assert resp.status == "PENDING"


@pytest.mark.asyncio
async def test_get_history_filters_by_type_and_status():
    """`get_history` が `job_type` と `status` で正しくフィルタすること。"""
    j1 = DummyJob(id=1, status="COMPLETED", batch_type="JPX_ALL_STOCKS")
    j2 = DummyJob(id=2, status="RUNNING", batch_type="JPX_ALL_STOCKS")
    repo = DummyRepo(by_type=[j1, j2], recent=[j1, j2])

    # job_type 指定で取得
    result = await batch_module.get_history(
        job_type=SimpleNamespace(value="JPX_ALL_STOCKS"), status=None, repo=repo
    )
    assert len(result) == 2

    # status 指定で絞り込み
    result2 = await batch_module.get_history(job_type=None, status="COMPLETED", repo=repo)
    assert all(r.status == "COMPLETED" for r in result2)


@pytest.mark.asyncio
async def test_cancel_job_not_found_raises():
    """キャンセル対象がない場合は `RecordNotFoundError` を返すこと。"""
    repo = DummyRepo(cancel_result=None)
    with pytest.raises(RecordNotFoundError):
        await batch_module.cancel_job(123, repo=repo)


@pytest.mark.asyncio
async def test_cancel_job_returns_job_when_found():
    """キャンセル成功時にキャンセル済みジョブを返すこと。"""
    job = DummyJob(id=250, status="CANCELLED", batch_type="JPX_ALL_STOCKS")
    repo = DummyRepo(cancel_result=job)
    resp = await batch_module.cancel_job(250, repo=repo)
    assert resp.job_id == "250"
    assert resp.status == "CANCELLED"


def test__job_to_response_dict_normalization():
    """内部ユーティリティ `_job_to_response_dict` の出力整形を検証する。"""
    # ORM のようなダミーオブジェクト（各種属性を持たせる）を作成
    obj = SimpleNamespace(
        id=55,
        batch_type="JPX_ALL_STOCKS",
        status="running",
        total_stocks=100,
        processed_stocks=25,
        successful_stocks=20,
        failed_stocks=5,
        start_time=None,
        end_time=None,
        params={"timeframe": "1d"},
    )

    d = batch_module._job_to_response_dict(obj)
    assert d["job_id"] == "55"
    assert d["job_type"] == "JPX_ALL_STOCKS"
    assert d["status"] == "RUNNING"
    # 進捗は float（0.0〜100.0）で返ること
    assert isinstance(d["progress"], float)
