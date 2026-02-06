from __future__ import annotations

import asyncio as _asyncio
import logging
from typing import List, Optional

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from fastapi import APIRouter, Depends

from app.api.dependencies.repositories import get_batch_execution_repository
from app.exceptions.database import RecordNotFoundError
from app.repositories.batch_execution_repository import BatchExecutionRepository
from app.schemas.batch import BatchExecutionResponse, JobType
from app.utils.database import get_db

router = APIRouter(tags=["batch"])

logger = logging.getLogger(__name__)


def _log_memory_usage(context: str) -> None:
    """メモリ使用状況をログ出力するヘルパー関数.

    Args:
        context (str): ログ出力時のコンテキスト説明

    Returns:
        None
    """
    if not PSUTIL_AVAILABLE:
        return

    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)

        logger.info(
            "[Resource Monitor] %s - Memory: %.2f MB, CPU: %.2f%%",
            context,
            memory_mb,
            cpu_percent,
        )
    except Exception:
        logger.exception("Failed to log memory usage")


async def _commit_with_rollback(session, context: str, job_id: int) -> None:
    """セッションをコミットし、失敗時にロールバックを試みるユーティリティ.

    Args:
        session: データベースセッション
        context (str): ログ出力時のコンテキスト説明
        job_id (int): 対象ジョブのID

    Returns:
        None
    """
    try:
        await session.commit()
    except Exception:
        logger.exception(
            "Failed to commit session after %s for job %s",
            context,
            job_id,
        )
        try:
            await session.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback session after commit failure for job %s",
                job_id,
            )


# pylint: disable=too-many-locals
def _job_to_response_dict(job) -> dict:
    """ORM の `BatchExecution` インスタンスを API レスポンス用 dict に変換するヘルパー.

    正規化ポイント:
    - DB の `batch_type` -> API の `job_type`
    - `status` は大文字化して enum に合わせる
    - 日時は ISO 文字列に変換
    - success/failed カウント名をスキーマ名に合わせる
    """
    # safe access for optional attributes
    job_id = getattr(job, "id", None)
    batch_type = getattr(job, "batch_type", None)
    status = getattr(job, "status", None)
    total = getattr(job, "total_stocks", None)
    processed = getattr(job, "processed_stocks", None)
    success = getattr(job, "successful_stocks", None)
    failed = getattr(job, "failed_stocks", None)
    start_time = getattr(job, "start_time", None)
    end_time = getattr(job, "end_time", None)
    error_message = getattr(job, "error_message", None)
    params = getattr(job, "params", None)

    # progress は processed/total を使って計算（存在しない場合は None）
    progress = None
    try:
        if total and processed is not None and total > 0:
            progress = float(processed) / float(total) * 100.0
    except Exception:
        progress = None
    # Clamp progress to [0.0, 100.0] to satisfy response schema constraints
    if progress is not None:
        try:
            if progress < 0.0:
                progress = 0.0
            elif progress > 100.0:
                progress = 100.0
        except Exception:
            progress = None

    return {
        "job_id": str(job_id) if job_id is not None else None,
        "job_type": batch_type,
        "status": status.upper() if isinstance(status, str) else status,
        "params": params or {},
        "progress": progress,
        "success_count": success,
        "failed_count": failed,
        "error_message": error_message,
        "started_at": start_time.isoformat() if start_time else None,
        "finished_at": end_time.isoformat() if end_time else None,
    }


# stock-data chunk processing removed; stock-price batch processing is deprecated here


async def _await_pending_tasks(
    pending_tasks: set[_asyncio.Task], context: str | None = None
) -> None:
    """保留中の非同期タスクを待機して例外をログに記録するヘルパー.

    Args:
        pending_tasks (set[_asyncio.Task]): 待機対象のタスク集合
        context (Optional[str]): ログ出力時の任意コンテキスト

    Returns:
        None
    """
    if not pending_tasks:
        return

    try:
        pending_list = list(pending_tasks)
        await _asyncio.gather(*pending_list, return_exceptions=True)
    except Exception:
        if context:
            logger.exception("Error %s", context)
        else:
            logger.exception("Error while awaiting pending progress tasks")
    finally:
        pending_tasks.clear()


def _make_progress_handlers(job_id: int):
    """進捗更新用ハンドラ群を作成して返すファクトリ関数.

    Args:
        job_id (int): 進捗更新対象のジョブID

    Returns:
        tuple: `(pending_tasks, async_progress_callback, sync_wrapper)`。
            - pending_tasks (set[asyncio.Task]): 保留中タスク集合
            - async_progress_callback (Callable[[dict], Awaitable[None]]):
                非同期コールバック
            - sync_wrapper (Callable[[dict], None]): 同期ラッパー（非同期タスクをスケジュール）
    """
    pending_tasks: set[_asyncio.Task] = set()

    async def _progress_callback(progress: dict):
        async for inner_session in get_db():
            inner_repo = BatchExecutionRepository(inner_session)
            try:
                await inner_repo.update_progress(job_id, progress)
                try:
                    await inner_session.commit()
                except Exception:
                    logger.exception("Failed to commit progress update for job %s", job_id)
                    try:
                        await inner_session.rollback()
                    except Exception:
                        logger.exception(
                            "Failed to rollback inner session for job %s",
                            job_id,
                        )
            except Exception:
                logger.exception("Failed to update progress for job %s", job_id)
            break

    def _sync_progress_cb(p: dict):
        try:
            task = _asyncio.create_task(_progress_callback(p))
        except Exception:
            return

        pending_tasks.add(task)

        def _on_done(t: _asyncio.Task) -> None:
            pending_tasks.discard(t)
            try:
                exc = t.exception()
            except (RuntimeError, _asyncio.CancelledError):
                return
            if exc is not None:
                logger.exception("Progress callback task failed: %s", exc)

        task.add_done_callback(_on_done)

    return pending_tasks, _progress_callback, _sync_progress_cb


@router.get("/status/{job_id}", response_model=BatchExecutionResponse)
async def get_job_status(
    job_id: int,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    job = await repo.get(job_id)
    if job is None:
        raise RecordNotFoundError(message=f"Job with id {job_id} not found")
    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))


@router.get("/history", response_model=List[BatchExecutionResponse])
async def get_history(
    job_type: Optional[JobType] = None,
    status: Optional[str] = None,
    limit: int = 10,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    if job_type is not None:
        records = await repo.get_by_job_type(job_type.value)
    else:
        records = await repo.get_recent(limit=limit)

    if status is not None:
        records = [r for r in records if r.status == status]

    # ORM インスタンスをスキーマ互換の dict に変換して返す
    return [BatchExecutionResponse.model_validate(_job_to_response_dict(r)) for r in records]


@router.delete("/cancel/{job_id}", response_model=BatchExecutionResponse)
async def cancel_job(
    job_id: int,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    job = await repo.cancel_job(job_id)
    if job is None:
        raise RecordNotFoundError(message=f"Job with id {job_id} not found")
    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))


# stock-data run_sequence and multi-timeframe helpers removed; handled elsewhere
