import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

import app.utils.database as db_mod
from app.models.batch_execution import BatchExecution
from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.utils.logger import get_logger

pytestmark = pytest.mark.integration

logger = get_logger(__name__)


@pytest.mark.anyio
async def test_create_and_persist_batch_execution(monkeypatch):
    """
    Integration テスト: `BatchExecutionRepository` を使って実際の DB にレコードを作成、
    完了処理を行い、永続化された内容を artifacts にダンプする。

    前提:
    - `app.utils.database.get_database_url()` がテスト用Postgresの接続文字列を返すこと
    - テーブルは既に存在している（スキーマは作成済みであることを想定）
    """

    try:
        DATABASE_URL = db_mod.get_database_url()
    except Exception as exc:  # pragma: no cover - 環境未設定ならスキップ
        pytest.skip(f"Skipping integration test: missing DB config ({exc})")

    engine = create_async_engine(DATABASE_URL, echo=False)

    # テスト用エンジンに差し替え
    monkeypatch.setattr(db_mod, "get_engine", lambda: engine)

    # キャッシュクリア
    try:
        db_mod.get_session_maker.cache_clear()
    except Exception:
        pass
    try:
        db_mod.get_engine.cache_clear()
    except Exception:
        pass

    session_maker = db_mod.get_session_maker()

    # 実際にリポジトリ経由でレコードを作成 -> 完了マーク
    async with session_maker() as session:
        repo = BatchExecutionRepository(session=session)

        created = await repo.create_job(batch_type="integration_test_job")
        assert created is not None

        # mark_completed を呼び出して集計・終了時刻をセット
        completed = await repo.mark_completed(
            record_id=getattr(created, "id"), success_count=3, failed_count=1
        )
        assert completed is not None
        assert completed.status == "completed"

        # トランザクションをコミットして永続化
        await session.commit()

    # 検証: 新しいセッションで永続化確認し、artifact に出力
    async with session_maker() as verify_session:
        result = await verify_session.execute(select(BatchExecution))
        rows = result.scalars().all()
        assert len(rows) >= 1

        # artifacts 出力
        import csv
        import os
        from datetime import datetime, timezone

        artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        fname = f"batch_executions_dump_{ts}.csv"
        out_path = os.path.join(artifacts_dir, fname)

        fieldnames = [
            "id",
            "batch_type",
            "status",
            "total_stocks",
            "processed_stocks",
            "successful_stocks",
            "failed_stocks",
            "start_time",
            "end_time",
            "error_message",
            "created_at",
        ]

        try:
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    row_data = {
                        "id": getattr(r, "id", None),
                        "batch_type": getattr(r, "batch_type", None),
                        "status": getattr(r, "status", None),
                        "total_stocks": getattr(r, "total_stocks", None),
                        "processed_stocks": (
                            getattr(r, "processed_stocks", None)
                        ),
                        "successful_stocks": (
                            getattr(r, "successful_stocks", None)
                        ),
                        "failed_stocks": getattr(r, "failed_stocks", None),
                        "start_time": getattr(r, "start_time", None),
                        "end_time": getattr(r, "end_time", None),
                        "error_message": getattr(r, "error_message", None),
                        "created_at": getattr(r, "created_at", None),
                    }
                    writer.writerow(row_data)
            logger.info("Wrote batch_executions dump to %s", out_path)
        except Exception as e:  # pragma: no cover - artifact write
            logger.error("Failed to write artifact: %s", e)

    # テーブル作成・削除は行わない（テーブルは既に存在している前提）
