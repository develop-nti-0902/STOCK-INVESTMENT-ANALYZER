from __future__ import annotations

import asyncio
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.api.dependencies.repositories import get_batch_execution_repository
from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.schemas.batch import BatchExecutionResponse, BatchJobParams, JobType
from app.utils.database import get_session_maker

router = APIRouter()


@router.post(
    "/stock-data/single",
    response_model=BatchExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_single_stock_job(
    params: BatchJobParams,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    """単一銘柄のデータ取得ジョブを作成して返す"""
    job = await repo.create_job(batch_type=JobType.SINGLE_STOCK.value)
    return job


@router.post(
    "/stock-data/jpx-all",
    response_model=BatchExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_jpx_all_job(
    params: BatchJobParams,
    background_tasks: BackgroundTasks,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    """JPX全銘柄一括取得ジョブを作成しバックグラウンドで処理を開始する"""
    job = await repo.create_job(batch_type=JobType.JPX_ALL_STOCKS.value)

    async def _process(job_id: int, p: dict):
        # セッションを新規作成して Repository を作成し、状態更新を行う
        session_maker = get_session_maker()
        async with session_maker() as session:
            repo2 = BatchExecutionRepository(session)
            await repo2.update_status(job_id, "running")
            # 実際の処理は別モジュールで行う想定。ここでは最小限で完了マークを付与。
            await repo2.mark_completed(job_id, success_count=0, failed_count=0)

    # 非同期タスクとして起動（BackgroundTasks 経由でイベントループ上にタスクを作る）
    background_tasks.add_task(
        asyncio.create_task, _process(job.id, params.model_dump())
    )

    return job


@router.get("/status/{job_id}", response_model=BatchExecutionResponse)
async def get_job_status(
    job_id: int,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


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

    return records


@router.delete("/cancel/{job_id}", response_model=BatchExecutionResponse)
async def cancel_job(
    job_id: int,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    job = await repo.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job
