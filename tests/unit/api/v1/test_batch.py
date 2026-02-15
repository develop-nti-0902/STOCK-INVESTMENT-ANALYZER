"""Unit tests for app.api.v1.batch helpers."""

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.api.v1 import batch as batch_module
from app.exceptions.database import RecordNotFoundError


def make_job(**kwargs):
    """Create a simple namespace object and set attributes from kwargs."""
    obj = SimpleNamespace()
    for k, v in kwargs.items():
        setattr(obj, k, v)
    return obj


def test_job_to_response_dict_basic():
    """基本的なジョブ変換が正しく行われることを検証する."""
    start = datetime(2024, 1, 1, 0, 0, 0)
    job = make_job(
        id=1,
        batch_type="refresh",
        status="running",
        total_stocks=10,
        processed_stocks=5,
        successful_stocks=4,
        failed_stocks=1,
        start_time=start,
        end_time=None,
        params={"k": "v"},
        error_message=None,
    )

    d = batch_module._job_to_response_dict(job)

    assert d["job_id"] == "1"
    assert d["job_type"] == "refresh"
    assert d["status"] == "RUNNING"
    assert d["progress"] == pytest.approx(50.0)
    assert d["started_at"] == start.isoformat()
    assert d["finished_at"] is None


def test_job_to_response_dict_clamps_progress():
    """進捗率が100%を超えた場合にクランプされることを確認する."""
    job = make_job(id=2, batch_type="a", status="ok", total_stocks=1, processed_stocks=5)
    d = batch_module._job_to_response_dict(job)
    assert d["progress"] == 100.0


@pytest.mark.asyncio
async def test_await_pending_tasks_handles_exception(caplog):
    """例外を投げるタスクがあっても待機処理が例外を透過しないことを確認する."""

    async def _bad():
        raise RuntimeError("fail")

    task = asyncio.create_task(_bad())
    pending = {task}

    # should not raise, and pending cleared
    await batch_module._await_pending_tasks(pending, context="test")
    assert len(pending) == 0


class DummyJob:
    """Dummy job object used to simulate job attributes for tests."""

    def __init__(self, **kwargs):
        """Initialize dummy job with provided attributes."""
        for k, v in kwargs.items():
            setattr(self, k, v)


class DummyRepo:
    """最小限のモック実装（BatchExecutionRepository相当）."""

    def __init__(self, get_result=None, by_type=None, recent=None, cancel_result=None):
        """Initialize DummyRepo with configurable return values."""
        self._get = get_result
        self._by_type = by_type or []
        self._recent = recent or []
        self._cancel = cancel_result

    async def get(self, job_id: int):
        """Return configured single job result."""
        return self._get

    async def get_by_job_type(self, job_type: str):
        """Return configured list of jobs filtered by type."""
        return self._by_type

    async def get_recent(self, limit: int = 10):
        """Return configured list of recent jobs (respecting `limit`)."""
        return self._recent

    async def cancel_job(self, job_id: int):
        """Return configured cancel result for given job id."""
        return self._cancel


@pytest.mark.asyncio
async def test_get_job_status_not_found_raises():
    """ジョブが存在しない場合は `RecordNotFoundError` を返すこと."""
    repo = DummyRepo(get_result=None)
    with pytest.raises(RecordNotFoundError):
        await batch_module.get_job_status(1, repo=repo)


@pytest.mark.asyncio
async def test_get_job_status_returns_job():
    """存在するジョブは `BatchExecutionResponse` として返されること."""
    job = DummyJob(id=7, status="PENDING", batch_type="JPX_ALL_STOCKS", total_stocks=0)
    repo = DummyRepo(get_result=job)

    resp = await batch_module.get_job_status(7, repo=repo)
    assert resp.job_id == "7"
    assert resp.status == "PENDING"


@pytest.mark.asyncio
async def test_get_history_filters_by_type_and_status():
    """`get_history` が `job_type` と `status` で正しくフィルタすること."""
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
    """キャンセル対象がない場合は `RecordNotFoundError` を返すこと."""
    repo = DummyRepo(cancel_result=None)
    with pytest.raises(RecordNotFoundError):
        await batch_module.cancel_job(123, repo=repo)


@pytest.mark.asyncio
async def test_cancel_job_returns_job_when_found():
    """キャンセル成功時にキャンセル済みジョブを返すこと."""
    job = DummyJob(id=250, status="CANCELLED", batch_type="JPX_ALL_STOCKS")
    repo = DummyRepo(cancel_result=job)
    resp = await batch_module.cancel_job(250, repo=repo)
    assert resp.job_id == "250"
    assert resp.status == "CANCELLED"


def test__job_to_response_dict_normalization():
    """内部ユーティリティ `_job_to_response_dict` の出力整形を検証する."""
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
