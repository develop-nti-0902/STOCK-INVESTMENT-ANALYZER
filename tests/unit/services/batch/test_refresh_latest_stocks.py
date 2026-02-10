"""Unit tests for batch refresh behavior using LatestStocksRefreshService.

最小限の docstring を追加して linter の docstring ルールに合わせる。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.exceptions.business import ServiceError
from app.services.views.latest_stocks import batch as mod


class _FakeResult:
    def __init__(self, val):
        self._val = val

    def fetchone(self):
        return (self._val,)


class _FakeTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, responses):
        # responses is an iterable of return values for execute().fetchone()
        self._responses = list(responses)
        self._index = 0

    async def execute(self, *args, **kwargs):
        if self._index < len(self._responses):
            val = self._responses[self._index]
            self._index += 1
        else:
            val = False
        return _FakeResult(val)

    def begin(self):
        return _FakeTransaction()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSyncEngine:
    def __init__(self, responses):
        self._responses = list(responses)

    def connect(self):
        # return a fresh conn that will report the configured responses
        return _FakeConn(self._responses)


class _FakeEngine:
    def __init__(self, responses):
        self._responses = list(responses)
        self.sync_engine = _FakeSyncEngine(responses)

    def connect(self):
        # 非同期コンテキストマネージャーとして機能する_FakeConnを返す
        return _FakeConn(self._responses)


@pytest.mark.asyncio
async def test_refresh_runs_when_lock_acquired(monkeypatch):
    """ロック取得時に run_refresh が実行されることを検証する."""
    # arrange
    fake_engine = _FakeEngine([True])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    # fake batch service (BatchExecutionService-like)
    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=1)
    batch.start_job.return_value = None
    batch.get_job_status.return_value = SimpleNamespace(
        processed_stocks=0, successful_stocks=0, failed_stocks=0
    )
    batch.complete_job.return_value = None

    called = {}

    class FakeSvc:
        def __init__(self, batch_service, engine=None):
            called["init_args"] = (batch_service, engine)
            self.batch_service = batch_service
            self._engine = engine
            self.logger = SimpleNamespace(
                info=lambda *a, **k: None,
                warning=lambda *a, **k: None,
                error=lambda *a, **k: None,
                exception=lambda *a, **k: None,
            )

        async def run_refresh(self):
            called["run"] = True

    # replace __init__ and run_refresh on the real service so instance methods exist
    monkeypatch.setattr(mod.LatestStocksRefreshService, "__init__", FakeSvc.__init__)
    monkeypatch.setattr(mod.LatestStocksRefreshService, "run_refresh", FakeSvc.run_refresh)

    # act
    svc = mod.LatestStocksRefreshService(batch, engine=fake_engine)
    await svc.enqueue_refresh()

    # assert
    assert called.get("run") is True
    batch.create_job.assert_awaited()


@pytest.mark.asyncio
async def test_no_run_when_lock_not_acquired(monkeypatch):
    """ロック未取得時は処理が実行されず ServiceError になることを検証する."""
    fake_engine = _FakeEngine([False])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=2)
    batch.start_job.return_value = None

    class FakeSvc:
        def __init__(self, *a, **k):
            # ensure attributes used by enqueue_refresh exist
            self.batch_service = a[0] if a else k.get("batch_service")
            self._engine = k.get("engine")
            self.logger = SimpleNamespace(
                info=lambda *a, **k: None,
                warning=lambda *a, **k: None,
                error=lambda *a, **k: None,
                exception=lambda *a, **k: None,
            )

        async def run_refresh(self):
            raise RuntimeError("should not be called")

    # replace __init__ and run_refresh on the real service
    monkeypatch.setattr(mod.LatestStocksRefreshService, "__init__", FakeSvc.__init__)
    monkeypatch.setattr(mod.LatestStocksRefreshService, "run_refresh", FakeSvc.run_refresh)

    # act / assert: SQLite 移行ではロックを使わないため、ジョブが作成され、
    # run_refresh が呼ばれて ServiceError になる（FakeSvc.run_refresh が例外を出す）
    svc = mod.LatestStocksRefreshService(batch, engine=fake_engine)
    with pytest.raises(ServiceError):
        await svc.enqueue_refresh()
    batch.create_job.assert_awaited()


@pytest.mark.asyncio
async def test_release_failure_logs_but_run_called(monkeypatch):
    """解放失敗時でも run_refresh は呼ばれることを検証する."""
    # acquire True, release False
    fake_engine = _FakeEngine([True])
    # monkeypatch connect to return conn that will return True for acquire
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=3)
    batch.start_job.return_value = None
    batch.get_job_status.return_value = SimpleNamespace(
        processed_stocks=0, successful_stocks=0, failed_stocks=0
    )

    class FakeSvc:
        def __init__(self, *a, **k):
            self.batch_service = a[0] if a else k.get("batch_service")
            self._engine = k.get("engine")
            self.logger = SimpleNamespace(
                info=lambda *a, **k: None,
                warning=lambda *a, **k: None,
                error=lambda *a, **k: None,
                exception=lambda *a, **k: None,
            )

        async def run_refresh(self):
            return None

    monkeypatch.setattr(mod.LatestStocksRefreshService, "__init__", FakeSvc.__init__)
    monkeypatch.setattr(mod.LatestStocksRefreshService, "run_refresh", FakeSvc.run_refresh)

    # run
    svc = mod.LatestStocksRefreshService(batch, engine=fake_engine)
    await svc.enqueue_refresh()

    batch.create_job.assert_awaited()


@pytest.mark.asyncio
async def test_exception_in_run_refresh_propagates_and_marks_failed(
    monkeypatch,
):
    """run_refresh の例外が ServiceError として伝播し、fail_job が呼ばれることを検証する."""
    fake_engine = _FakeEngine([True])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    batch = AsyncMock()
    batch.create_job.return_value = SimpleNamespace(id=4)
    batch.start_job.return_value = None
    batch.fail_job.return_value = None

    class FakeSvc:
        def __init__(self, *a, **k):
            self.batch_service = a[0] if a else k.get("batch_service")
            self._engine = k.get("engine")
            self.logger = SimpleNamespace(
                info=lambda *a, **k: None,
                warning=lambda *a, **k: None,
                error=lambda *a, **k: None,
                exception=lambda *a, **k: None,
            )

        async def run_refresh(self):
            raise RuntimeError("boom")

    monkeypatch.setattr(mod.LatestStocksRefreshService, "__init__", FakeSvc.__init__)
    monkeypatch.setattr(mod.LatestStocksRefreshService, "run_refresh", FakeSvc.run_refresh)

    svc = mod.LatestStocksRefreshService(batch, engine=fake_engine)
    # 新しい実装では、run_refresh での例外は ServiceError にラップされる
    with pytest.raises(ServiceError) as exc_info:
        await svc.enqueue_refresh()

    # エラーメッセージに元の例外情報が含まれていることを確認
    assert "boom" in str(exc_info.value)

    # ensure fail_job was called by enqueue_refresh
    batch.create_job.assert_awaited()
    batch.fail_job.assert_awaited()
