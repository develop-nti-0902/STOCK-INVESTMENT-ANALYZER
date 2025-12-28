from __future__ import annotations

import asyncio as _asyncio
from datetime import date, datetime
from typing import List, Optional, Union, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi import status as http_status

from app.api.dependencies.repositories import get_batch_execution_repository
from app.api.dependencies.services import get_stock_price_service
from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.schemas.batch import BatchExecutionResponse, BatchJobParams, JobType
from app.services.market_data.stock_price import StockPriceService
from app.utils.database import get_session_maker

router = APIRouter()


@router.post(
    "/stock-data/single",
    response_model=BatchExecutionResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def start_single_stock_job(
    params: BatchJobParams,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    """単一銘柄のデータ取得ジョブを作成して返す"""
    # 引数は API 用のシグネチャとして必要だが関数内で使用しないため参照しておく
    _ = params

    job = await repo.create_job(batch_type=JobType.SINGLE_STOCK.value)
    return job


@router.post(
    "/stock-data/jpx-all",
    response_model=BatchExecutionResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def start_jpx_all_job(
    params: BatchJobParams,
    background_tasks: BackgroundTasks,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
    service: StockPriceService = Depends(get_stock_price_service),
):
    """JPX全銘柄一括取得ジョブを作成しバックグラウンドで処理を開始する"""
    # 引数参照は unused-argument を避けるために行う（実処理では未使用）
    _ = params
    _ = background_tasks

    job = await repo.create_job(batch_type=JobType.JPX_ALL_STOCKS.value)

    # バックグラウンドタスクを登録して既存の StockPriceService を呼び出す
    background_tasks.add_task(
        process_jpx_all_stocks, job.id, params.model_dump(), service
    )

    return job


async def process_jpx_all_stocks(
    job_id: int, params: dict, service: StockPriceService
) -> None:
    """JPX全銘柄取得タスクの簡易実装。

    実環境では銘柄リスト取得やStockPriceServiceの呼び出しを行う想定。
    ここでは`BatchExecutionRepository`のステータス更新・進捗更新・完了マークを行う。
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = BatchExecutionRepository(session)
        # 実行開始を記録
        await repo.update_status(job_id, "running")

        # progress_callback を作成して service の進捗をこのジョブへ反映する
        async def _progress_callback(progress: dict):
            try:
                await repo.update_progress(job_id, progress)
            except Exception:
                # ログは既存のユーティリティに任せる
                pass

        # service.fetch_all_jpx_stocks は progress_callback を同期コールバックとして想定している
        # ここでは非同期から呼ぶため、ラッパーで同期的に呼ぶ
        def _sync_progress_cb(p: dict):
            # 非同期関数をスケジュールして進捗を反映する
            try:
                _asyncio.create_task(_progress_callback(p))
            except Exception:
                pass

        try:
            result = await service.fetch_all_jpx_stocks(
                timeframe=cast(str, params.get("timeframe")),
                start_date=cast(
                    Union[date, datetime, str], params.get("start_date")
                ),
                end_date=cast(
                    Union[date, datetime, str], params.get("end_date")
                ),
                market=params.get("market"),
                progress_callback=_sync_progress_cb,
            )

            # service の返却結果に基づき完了マークを付与
            success = int(result.get("success", 0))
            failed = int(result.get("failed", 0))
            await repo.mark_completed(
                job_id, success_count=success, failed_count=failed
            )

        except Exception:  # pylint: disable=broad-except
            # 失敗時は fail 情報を残す
            try:
                await repo.update_status(job_id, "failed")
            except Exception:
                pass


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
