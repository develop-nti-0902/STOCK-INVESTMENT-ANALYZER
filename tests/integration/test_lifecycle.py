from fastapi.testclient import TestClient

import app.main as main_mod


def test_startup_and_shutdown_call_db_lifecycle(monkeypatch):
    """
    FastAPIの起動/終了でDBライフサイクル（get_engine().connect() / close_db()）
    が呼ばれることを検証する統合テスト。

    実際のDB接続は行わず、モックのエンジン/コネクションで副作用を検知する。
    """
    called = {"connect": False, "close_db": False}

    class DummyConn:
        async def close(self):
            called["connect"] = True

    class DummyEngine:
        async def connect(self):
            return DummyConn()

    async def dummy_close_db():
        called["close_db"] = True

    # app.main モジュールに定義済みの名前を差し替える
    def dummy_get_engine():
        return DummyEngine()

    monkeypatch.setattr(main_mod, "get_engine", dummy_get_engine)
    monkeypatch.setattr(main_mod, "close_db", dummy_close_db)

    with TestClient(main_mod.app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    # TestClient のコンテキストを抜けると shutdown ハンドラが実行される
    assert called["connect"] is True
    assert called["close_db"] is True
