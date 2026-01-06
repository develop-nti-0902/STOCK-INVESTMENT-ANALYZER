from __future__ import annotations

import asyncio as _asyncio
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union, cast

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi import status as http_status

from app.api.dependencies.repositories import get_batch_execution_repository
from app.api.dependencies.services import get_stock_price_service
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.schemas.batch import BatchExecutionResponse, BatchJobParams, JobType
from app.schemas.stock_data import StockPriceCreate
from app.services.batch.batch_execution_service import BatchExecutionContext
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


async def _process_chunk_multi(
    chunk: List[str],
    service: StockPriceService,
    timeframe_param: str,
    params: dict,
) -> tuple[int, int, List[Dict[str, Any]]]:
    """チャンク単位の処理を切り出したヘルパー。

    Returns:
        success_inc, failed_inc, errors_list
    """
    success_inc = 0
    failed_inc = 0
    errors: List[Dict[str, Any]] = []

    # fetch
    results = await service.fetcher.fetch_multi_yfinance(
        chunk,
        timeframe=timeframe_param,
        start_date=params.get("start_date"),
        end_date=params.get("end_date"),
    )

    payloads: List[Dict[str, Any]] = []
    for sym, sd_list in results.items():
        valid_models: List[Any] = []
        for sd in sd_list:
            res = service.validator.validate(sd)
            if res.is_valid:
                valid_models.append(sd)

        if not valid_models:
            failed_inc += 1
            errors.append({"symbol": sym, "errors": ["no valid data"]})
            continue

        try:
            records = service.converter.to_saver_records(
                cast(List[StockPriceCreate], valid_models)
            )
        except Exception as exc:  # pragma: no cover - defensive
            failed_inc += 1
            errors.append({"symbol": sym, "errors": [str(exc)]})
            continue

        payloads.append(
            {"symbol": sym, "timeframe": timeframe_param, "records": records}
        )

    if payloads:
        try:
            await service.saver.save_batch(payloads)
            success_inc += len(payloads)
        except Exception:
            failed_inc += len(payloads)

    return success_inc, failed_inc, errors


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
    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))


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

    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))


@router.post(
    "/stock-data/jpx-all/multi",
    response_model=BatchExecutionResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def start_jpx_all_multi_job(
    params: BatchJobParams,
    background_tasks: BackgroundTasks,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
    service: StockPriceService = Depends(get_stock_price_service),
) -> BatchExecutionResponse:
    """JPX 全銘柄をマルチティッカー API で取得するジョブを作成してバックグラウンドで実行します.

    `params` の中に `list_batch_size` を含めると、fetch_multi_yfinance に渡す銘柄数を制御できます。
    """
    _ = params
    _ = background_tasks

    job = await repo.create_job(batch_type=JobType.JPX_ALL_STOCKS.value)

    # マルチ取得用のバックグラウンドタスクを登録
    background_tasks.add_task(
        process_jpx_all_stocks_multi, job.id, params.model_dump(), service
    )

    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))


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
                    pending_list = list(pending_tasks)
                    await _asyncio.gather(
                        *pending_list, return_exceptions=True
                    )
                except Exception:
                    logger.exception(
                        "Error while awaiting pending progress tasks "
                        "after failure"
                    )
                finally:
                    pending_tasks.clear()


async def process_jpx_all_stocks_multi(
    job_id: int, params: dict, service: StockPriceService
) -> None:
    """JPX全銘柄をマルチティッカー取得で処理するバックグラウンドタスク.

    `params` には `list_batch_size` を含めることで、一度に fetch_multi_yfinance に渡す銘柄数を
    指定できます。指定が無ければデフォルトで 50 を使います。
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        repo = BatchExecutionRepository(session)
        await repo.update_status(job_id, "running")
        try:
            await session.commit()
        except Exception:
            msg = (
                "Failed to commit session after setting status 'running' "
                "for job %s"
            )
            logger.exception(msg, job_id)
            try:
                await session.rollback()
            except Exception:
                msg = (
                    "Failed to rollback session after commit failure "
                    "for job %s"
                )
                logger.exception(msg, job_id)

        pending_tasks, _progress_callback, _sync_progress_cb = (
            _make_progress_handlers(job_id)
        )

        try:
            # 銘柄リスト取得
            if service.stock_master_service is None:
                raise ServiceError("StockMasterService is required")

            market = params.get("market")
            if market:
                symbols = (
                    await service.stock_master_service.get_symbols_by_market(
                        market
                    )
                )
            else:
                symbols = (
                    await service.stock_master_service.get_all_active_symbols()
                )

            total = len(symbols)
            list_batch_size = int(params.get("list_batch_size") or 50)

            # BatchExecutionContext imported at module level

            success = 0
            failed = 0
            errors = []

            timeframe_param = cast(str, params.get("timeframe") or "1d")

            async with BatchExecutionContext(
                service.batch_service,
                job_type="jpx_all_multi",
                params={
                    "timeframe": timeframe_param,
                    "market": market,
                    "list_batch_size": list_batch_size,
                },
            ) as ctx:
                # 銘柄を list_batch_size ごとのチャンクに分割し、fetch_multi_yfinance を呼ぶ
                for i in range(0, total, list_batch_size):
                    chunk = symbols[i : i + list_batch_size]
                    # チャンク処理をヘルパーに委譲
                    s_inc, f_inc, errs = await _process_chunk_multi(
                        chunk, service, timeframe_param, params
                    )
                    success += s_inc
                    failed += f_inc
                    if errs:
                        errors.extend(errs)

                    # 進捗コールバックの呼び出しとコンテキスト更新
                    if _sync_progress_cb is not None:
                        try:
                            _sync_progress_cb(
                                {
                                    "total": total,
                                    "processed": success + failed,
                                    "success": success,
                                    "failed": failed,
                                }
                            )
                        except Exception:
                            logger.exception("Progress callback failed")

                    try:
                        await ctx.update_progress(
                            processed=success + failed,
                            total=total,
                            success=success,
                            failed=failed,
                        )
                    except Exception:
                        logger.exception("Failed to update batch progress")

            # 保留中の進捗更新タスクを待機する
            await _await_pending_tasks(
                pending_tasks, "while awaiting pending progress tasks"
            )

            # finalize job
            try:
                await repo.mark_completed(
                    job_id, success_count=success, failed_count=failed
                )
                await _commit_with_rollback(session, "mark_completed", job_id)
            except Exception:
                logger.exception("Failed to mark_completed for job %s", job_id)

        except Exception:  # pylint: disable=broad-except
            logger.exception(
                "process_jpx_all_stocks_multi failed for job %s", job_id
            )
            try:
                await repo.update_status(job_id, "failed")
                await _commit_with_rollback(
                    session, "setting status 'failed'", job_id
                )
            except Exception:
                logger.exception(
                    "Failed to update status to 'failed' for job %s", job_id
                )
            if pending_tasks:
                try:
                    pending_list = list(pending_tasks)
                    await _asyncio.gather(
                        *pending_list, return_exceptions=True
                    )
                except Exception:
                    msg = (
                        "Error while awaiting pending progress tasks "
                        "after failure"
                    )
                    logger.exception(msg)
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
    return [
        BatchExecutionResponse.model_validate(_job_to_response_dict(r))
        for r in records
    ]


@router.delete("/cancel/{job_id}", response_model=BatchExecutionResponse)
async def cancel_job(
    job_id: int,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
):
    job = await repo.cancel_job(job_id)
    if job is None:
        raise RecordNotFoundError(message=f"Job with id {job_id} not found")
    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))
