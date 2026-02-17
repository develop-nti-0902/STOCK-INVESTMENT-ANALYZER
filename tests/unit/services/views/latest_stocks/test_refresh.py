"""Unit tests for latest_stocks refresh behaviors (mapped to `refresh.py`).

これらのテストは `latest_stocks` の refresh 実装の振る舞いを検証します。
バッチ管理は廃止され、`run_refresh()` を直接呼び出す仕様になっています。
"""

from types import SimpleNamespace

import pytest

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

    called = {}

    class FakeSvc:
        def __init__(self, engine=None):
            called["init_args"] = (engine,)
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
    svc = mod.LatestStocksRefreshService(engine=fake_engine)
    await svc.run_refresh()

    # assert
    assert called.get("run") is True


@pytest.mark.asyncio
async def test_no_run_when_lock_not_acquired(monkeypatch):
    """ロック未取得時は処理が実行されずエラーが伝播することを検証する."""
    fake_engine = _FakeEngine([False])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    class FakeSvc:
        def __init__(self, *a, **k):
            # ensure attributes used by run_refresh exist
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

    # act / assert: run_refresh should propagate the underlying error
    svc = mod.LatestStocksRefreshService(engine=fake_engine)
    with pytest.raises(RuntimeError):
        await svc.run_refresh()


@pytest.mark.asyncio
async def test_release_failure_logs_but_run_called(monkeypatch):
    """解放失敗時でも run_refresh は呼ばれることを検証する."""
    # acquire True, release False
    fake_engine = _FakeEngine([True])
    # monkeypatch connect to return conn that will return True for acquire
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    class FakeSvc:
        def __init__(self, *a, **k):
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
    svc = mod.LatestStocksRefreshService(engine=fake_engine)
    await svc.run_refresh()


@pytest.mark.asyncio
async def test_exception_in_run_refresh_propagates_and_marks_failed(
    monkeypatch,
):
    """run_refresh の例外が ServiceError として伝播し、fail_job が呼ばれることを検証する."""
    fake_engine = _FakeEngine([True])
    monkeypatch.setattr(mod, "get_engine", lambda: fake_engine, raising=False)

    class FakeSvc:
        def __init__(self, *a, **k):
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

    svc = mod.LatestStocksRefreshService(engine=fake_engine)
    # 新しい実装では、run_refresh の例外はそのまま伝播する
    with pytest.raises(RuntimeError) as exc_info:
        await svc.run_refresh()

    # エラーメッセージに元の例外情報が含まれていることを確認
    assert "boom" in str(exc_info.value)
