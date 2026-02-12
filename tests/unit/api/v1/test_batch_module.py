import asyncio
import types
from datetime import datetime, timedelta

import pytest

from app.api.v1 import batch as batch_mod


def test_log_memory_usage_no_psutil(monkeypatch):
    # Ensure path where psutil not available just returns without error
    monkeypatch.setattr(batch_mod, "PSUTIL_AVAILABLE", False)
    # Should not raise
    batch_mod._log_memory_usage("ctx")


def test_log_memory_usage_with_psutil(monkeypatch):
    # Provide fake psutil with Process() returning memory_info and cpu_percent
    fake_psutil = types.SimpleNamespace()

    class Proc:
        def memory_info(self):
            return types.SimpleNamespace(rss=1024 * 1024 * 10)

        def cpu_percent(self, interval=0.1):
            return 1.23

    fake_psutil.Process = lambda: Proc()
    monkeypatch.setattr(batch_mod, "PSUTIL_AVAILABLE", True)
    monkeypatch.setattr(batch_mod, "psutil", fake_psutil)
    # Should not raise
    batch_mod._log_memory_usage("ctx2")


@pytest.mark.asyncio
async def test_commit_with_rollback_calls_rollback_on_commit_failure():
    class Session:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

        async def commit(self):
            raise RuntimeError("commit failed")

        async def rollback(self):
            self.rolled_back = True

    s = Session()
    await batch_mod._commit_with_rollback(s, "ctx", job_id=1)
    assert s.rolled_back


def test_job_to_response_dict_formats_and_clamps():
    class Job:
        pass

    j = Job()
    j.id = 10
    j.batch_type = "type_x"
    j.status = "running"
    j.total_stocks = 4
    j.processed_stocks = 10  # > total to force clamp
    j.successful_stocks = 3
    j.failed_stocks = 1
    j.start_time = datetime(2020, 1, 1, 0, 0)
    j.end_time = datetime(2020, 1, 2, 0, 0)
    j.params = {"a": 1}

    res = batch_mod._job_to_response_dict(j)
    assert res["progress"] == 100.0
    assert res["job_id"] == str(10)
    assert res["status"] == "RUNNING"
    assert res["started_at"] == j.start_time.isoformat()


@pytest.mark.asyncio
async def test_await_pending_tasks_clears_and_handles_exceptions():
    # create a task that raises
    async def bad():
        raise RuntimeError("boom")

    t = asyncio.create_task(bad())
    pending = {t}
    await batch_mod._await_pending_tasks(pending, context="ctx")
    assert len(pending) == 0
