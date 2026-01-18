from __future__ import annotations

import asyncio as _asyncio
import logging
from datetime import date, datetime
from typing import List, Optional, Union, cast

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi import status as http_status

from app.api.dependencies.repositories import get_batch_execution_repository
from app.api.dependencies.services import get_stock_price_service
from app.exceptions.database import RecordNotFoundError
from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.schemas.batch import BatchExecutionResponse, BatchJobParams, JobType
from app.services.market_data.stock_price import StockPriceService
from app.utils.database import get_session_maker

router = APIRouter(tags=["batch"])

logger = logging.getLogger(__name__)


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
        await _asyncio.gather(*list(pending_tasks), return_exceptions=True)
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
        inner_session_maker = get_session_maker()
        async with inner_session_maker() as inner_session:
            inner_repo = BatchExecutionRepository(inner_session)
            try:
                await inner_repo.update_progress(job_id, progress)
                try:
                    await inner_session.commit()
                except Exception:
                    logger.exception(
                        "Failed to commit progress update for job %s", job_id
                    )
                    try:
                        await inner_session.rollback()
                    except Exception:
                        logger.exception(
                            "Failed to rollback inner session for job %s",
                            job_id,
                        )
            except Exception:
                logger.exception(
                    "Failed to update progress for job %s", job_id
                )

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


@router.post(
    "/stock-data/single",
    response_model=BatchExecutionResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def start_single_stock_job(
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
) -> BatchExecutionResponse:
    """単一銘柄のデータ取得ジョブを作成して返すエンドポイント.

    Args:
        repo (BatchExecutionRepository): バッチ実行リポジトリ

    Returns:
        BatchExecutionResponse: 作成されたジョブ情報
    """
    # このエンドポイントはジョブ作成のみを行うため、パラメータを受け取らない仕様に変更しました。
    job = await repo.create_job(batch_type=JobType.SINGLE_STOCK.value)
    return BatchExecutionResponse.model_validate(job)


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
) -> BatchExecutionResponse:
    """JPX全銘柄一括取得ジョブを作成し、バックグラウンド処理を開始するエンドポイント.

    Args:
        params (BatchJobParams): ジョブ実行パラメータ
        background_tasks (BackgroundTasks): FastAPI のバックグラウンドタスク
        repo (BatchExecutionRepository): バッチ実行リポジトリ
        service (StockPriceService): 株価収集サービス

    Returns:
        BatchExecutionResponse: 作成されたジョブ情報
    """
    # 引数参照は unused-argument を避けるために行う（実処理では未使用）
    _ = params
    _ = background_tasks

    job = await repo.create_job(batch_type=JobType.JPX_ALL_STOCKS.value)

    # バックグラウンドタスクを登録して既存の StockPriceService を呼び出す
    background_tasks.add_task(
        process_jpx_all_stocks, job.id, params.model_dump(), service
    )

    return BatchExecutionResponse.model_validate(job)


async def process_jpx_all_stocks(
    job_id: int, params: dict, service: StockPriceService
) -> None:
    """JPX全銘柄取得タスクの簡易実装.

    実環境では銘柄リスト取得や`StockPriceService`の呼び出しを行う想定。
    ここでは`BatchExecutionRepository`のステータス更新・進捗更新・完了マークを行う。

    Args:
        job_id (int): 対象ジョブID
        params (dict): ジョブパラメータ（`BatchJobParams.model_dump()`の結果）
        service (StockPriceService): 株価収集サービス

    Returns:
        None
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = BatchExecutionRepository(session)
        # 実行開始を記録
        await repo.update_status(job_id, "running")
        # ここで明示的にコミットしてステータス変更を永続化する
        try:
            await session.commit()
        except Exception:
            logger.exception(
                "Failed to commit session after setting "
                "status 'running' for job %s",
                job_id,
            )
            try:
                await session.rollback()
            except Exception:
                logger.exception(
                    "Failed to rollback session after commit "
                    "failure for job %s",
                    job_id,
                )

        # progress_callback を作成して service の進捗をこのジョブへ反映する
        pending_tasks, _progress_callback, _sync_progress_cb = (
            _make_progress_handlers(job_id)
        )

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
            # 完了マークを永続化
            await _commit_with_rollback(session, "mark_completed", job_id)

            # すべての進捗更新タスクが完了するのを待つ（例外はログに記録される）
            await _await_pending_tasks(
                pending_tasks, "while awaiting pending progress tasks"
            )

        except Exception:  # pylint: disable=broad-except
            # 元の例外をログに残す（スタックトレース含む）
            logger.exception(
                "process_jpx_all_stocks failed for job %s",
                job_id,
            )

            # 失敗時は fail 情報を残す（更新に失敗した場合もログを出す）
            try:
                await repo.update_status(job_id, "failed")
                await _commit_with_rollback(
                    session, "setting status 'failed'", job_id
                )
            except Exception:
                logger.exception(
                    "Failed to update status to 'failed' for job %s", job_id
                )
            # ジョブ失敗時もスケジュール済みの進捗更新を待つ
            if pending_tasks:
                try:
                    await _asyncio.gather(
                        *list(pending_tasks), return_exceptions=True
                    )
                except Exception:
                    logger.exception(
                        "Error while awaiting pending progress tasks "
                        "after failure"
                    )
                finally:
                    pending_tasks.clear()


@router.get("/status/{job_id}", response_model=BatchExecutionResponse)
async def get_job_status(
    job_id: int,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    job = await repo.get(job_id)
    if job is None:
        raise RecordNotFoundError(message=f"Job with id {job_id} not found")
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
        raise RecordNotFoundError(message=f"Job with id {job_id} not found")
    return job
