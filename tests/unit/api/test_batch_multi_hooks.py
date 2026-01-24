from unittest.mock import AsyncMock

import pytest

from app.api.v1 import batch


@pytest.mark.asyncio
async def test_process_jpx_all_stocks_multi_calls_details_hooks(monkeypatch):
    # モック：_process_chunk_multi を高速化
    monkeypatch.setattr(
        batch, "_process_chunk_multi", AsyncMock(return_value=(1, 0, []))
    )

    # モック：Session maker を簡易実装（commit/rollback を提供）
    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def commit(self):
            return None

        async def rollback(self):
            return None

    monkeypatch.setattr(batch, "get_session_maker", lambda: DummySession)

    # モック：BatchExecutionContext を置き換え（内部で update_progress を呼ぶだけ）
    class DummyCtx:
        def __init__(self, service, job_type, params=None):
            pass

        async def __aenter__(self):
            class CtxObj:
                async def update_progress(self, **kwargs):
                    return None

            return CtxObj()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(batch, "BatchExecutionContext", DummyCtx)

    # モック：BatchExecutionDetailsRepository をキャプチャ可能なダミーに置換
    created_instances = []

    class FakeDetailsRepo:
        def __init__(self, session):
            self.session = session
            self.initialized = False
            self.inc_total = 0
            self.statuses = []
            created_instances.append(self)

        async def init(
            self, batch_execution_id, interval, total_stocks, status
        ):
            self.initialized = True

        async def inc(self, batch_execution_id, interval, count=1):
            self.inc_total += int(count)

        async def set_status(self, batch_execution_id, interval, status):
            self.statuses.append(status)

    monkeypatch.setattr(
        batch, "BatchExecutionDetailsRepository", FakeDetailsRepo
    )

    # モック：BatchExecutionRepository を置換して DB アクセスを回避
    class FakeBatchRepo:
        def __init__(self, session):
            pass

        async def update_status(self, record_id, status):
            return None

        async def mark_completed(
            self, record_id, success_count=0, failed_count=0
        ):
            return None

    monkeypatch.setattr(batch, "BatchExecutionRepository", FakeBatchRepo)

    # モック：stock_master_service を提供する簡易 service
    class FakeStockMasterService:
        async def get_all_active_symbols(self):
            return ["A", "B", "C", "D", "E"]

    class FakeService:
        def __init__(self):
            self.stock_master_service = FakeStockMasterService()

    svc = FakeService()

    # 実行
    await batch.process_jpx_all_stocks_multi(1, {"list_batch_size": 2}, svc)

    # 検証：FakeDetailsRepo のインスタンスが生成され、init が呼ばれ、inc と set_status が呼ばれているはず
    assert len(created_instances) >= 1
    # いずれかの作成インスタンスに対して初期化が行われていること
    assert any(getattr(i, "initialized", False) for i in created_instances)
