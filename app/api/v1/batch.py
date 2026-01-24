from __future__ import annotations

import asyncio as _asyncio
import gc
import logging
from datetime import datetime as dt
from typing import Any, Dict, List, Optional, cast

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi import status as http_status

from app.api.dependencies.repositories import get_batch_execution_repository
from app.api.dependencies.services import get_stock_price_service
from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.repositories.batch_execution_details_repository import (
    BatchExecutionDetailsRepository,
)
from app.repositories.batch_execution_repository import (
    BatchExecutionRepository,
)
from app.schemas.batch import (
    BatchExecutionResponse,
    BatchJobParams,
    JobType,
    JPXAllMultiSequenceRequest,
    JPXAllMultiSequenceResponse,
)
from app.schemas.stock_data import StockPriceCreate
from app.services.batch.batch_execution_service import BatchExecutionContext
from app.services.market_data.stock_price import StockPriceService
from app.utils.database import get_session_maker

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


async def _process_chunk_multi(
    chunk: List[str],
    service: StockPriceService,
    timeframe_param: str,
    _params: dict,
) -> tuple[int, int, List[Dict[str, Any]]]:
    """チャンク単位の処理を切り出したヘルパー。

    Returns:
        success_inc, failed_inc, errors_list
    """
    success_inc = 0
    failed_inc = 0
    errors: List[Dict[str, Any]] = []

    # fetch
    results = await service.fetcher.fetch_batch(
        chunk,
        timeframe=timeframe_param,
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

    # チャンク処理後のリソース解放
    del results
    del payloads
    gc.collect()

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
    # 作成したジョブを確実に DB に残すため明示的にコミットする
    try:
        await repo.session.commit()
    except Exception:
        logger.exception(
            "Failed to commit session after creating job %s",
            getattr(job, "id", None),
        )
        try:
            await repo.session.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback session after commit failure for job %s",
                getattr(job, "id", None),
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

    # 明示コミットしてからバックグラウンドタスクを登録（競合を避ける）
    try:
        await repo.session.commit()
    except Exception:
        logger.exception(
            "Failed to commit session after creating job %s",
            getattr(job, "id", None),
        )
        try:
            await repo.session.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback session after commit failure for job %s",
                getattr(job, "id", None),
            )

    # マルチ取得用のバックグラウンドタスクを登録
    background_tasks.add_task(
        process_jpx_all_stocks_multi, int(job.id), params.model_dump(), service
    )

    return BatchExecutionResponse.model_validate(_job_to_response_dict(job))


# `process_jpx_all_stocks` removed: use multi-ticker endpoints.


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
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
                raise ServiceError(message="StockMasterService is required")

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

            # BatchExecutionDetails 用リポジトリ（interval 単位の進捗集計）
            details_repo = BatchExecutionDetailsRepository(session)

            # details レコードを初期化しておく
            try:
                await details_repo.init(
                    batch_execution_id=job_id,
                    interval=None,
                    total_stocks=total,
                    status="running",
                )
                await _commit_with_rollback(session, "init_details", job_id)
            except Exception:
                logger.exception(
                    "Failed to init batch execution details for job %s",
                    job_id,
                )

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

                    # details の処理済み数をインクリメント
                    try:
                        inc_count = int(s_inc or 0) + int(f_inc or 0)
                        if inc_count:
                            await details_repo.inc(job_id, None, inc_count)
                            try:
                                await session.commit()
                            except Exception:
                                logger.exception(
                                    "Failed to commit session for job %s",
                                    job_id,
                                )
                                try:
                                    await session.rollback()
                                except Exception:
                                    logger.exception(
                                        "Rollback failed for job %s",
                                        job_id,
                                    )
                    except Exception:
                        logger.exception(
                            "Failed to increment details for job %s",
                            job_id,
                        )

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
                pending_tasks,
                "while awaiting pending progress tasks",
            )

            # finalize job
            try:
                await repo.mark_completed(
                    job_id, success_count=success, failed_count=failed
                )
                # details のステータスも完了に更新
                try:
                    await details_repo.set_status(job_id, None, "completed")
                    await _commit_with_rollback(
                        session, "mark_completed", job_id
                    )
                except Exception:
                    logger.exception(
                        "Failed to set details status to completed for job %s",
                        job_id,
                    )
            except Exception:
                logger.exception(
                    "Failed to mark job completed for job %s", job_id
                )

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


@router.post(
    "/stock-data/jpx-all/multi/run_sequence",
    response_model=JPXAllMultiSequenceResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def run_jpx_all_multi_sequence(
    params: JPXAllMultiSequenceRequest,
    background_tasks: BackgroundTasks,
    repo: BatchExecutionRepository = Depends(get_batch_execution_repository),
    service: StockPriceService = Depends(get_stock_price_service),
) -> JPXAllMultiSequenceResponse:
    """JPX全銘柄を固定タイムフレーム（1d→1m→1h）で順次実行するエンドポイント.

    Args:
        params (JPXAllMultiSequenceRequest): バッチサイズを含むリクエストパラメータ
        background_tasks (BackgroundTasks): FastAPIのバックグラウンドタスク
        repo (BatchExecutionRepository): バッチ実行リポジトリ
        service (StockPriceService): 株価収集サービス

    Returns:
        JPXAllMultiSequenceResponse: ジョブIDと各タイムフレームの実行結果
    """
    job = await repo.create_job(
        batch_type=JobType.JPX_ALL_STOCKS.value,
    )

    # 明示コミットしてからバックグラウンドタスクを登録（競合を避ける）
    try:
        await repo.session.commit()
    except Exception:
        logger.exception(
            "Failed to commit session after creating job %s",
            getattr(job, "id", None),
        )
        try:
            await repo.session.rollback()
        except Exception:
            logger.exception(
                "Failed to rollback session after commit failure for job %s",
                getattr(job, "id", None),
            )

    background_tasks.add_task(
        process_jpx_all_multi_sequence,
        int(job.id),
        int(params.batch_size or 50),
        service,
    )

    return JPXAllMultiSequenceResponse(
        job_id=str(job.id),
        overall_status="PENDING",
        results=[],
    )


async def process_jpx_all_multi_sequence(
    job_id: int, batch_size: int, service: StockPriceService
) -> None:
    """JPX全銘柄を1d→1m→1hの順でマルチ取得するバックグラウンドタスク.

    Args:
        job_id (int): 対象ジョブID
        batch_size (int): 一度に処理する銘柄数
        service (StockPriceService): 株価収集サービス

    Returns:
        None
    """
    session_maker = get_session_maker()
    timeframes = ["1d", "1m", "1h"]
    results: List[Dict[str, Any]] = []

    # バッチ処理開始時のリソース状況
    _log_memory_usage(f"Batch job {job_id} started")

    async with session_maker() as session:
        repo = BatchExecutionRepository(session)
        await repo.update_status(job_id, "running")
        try:
            await session.commit()
        except Exception:
            logger.exception(
                "Failed to commit session after setting status 'running' "
                "for job %s",
                job_id,
            )
            try:
                await session.rollback()
            except Exception:
                logger.exception(
                    "Failed to rollback session after commit failure "
                    "for job %s",
                    job_id,
                )

        try:
            for timeframe in timeframes:
                # タイムフレーム処理前のリソース状況
                _log_memory_usage(
                    f"Before timeframe {timeframe} for job {job_id}"
                )

                result = await _execute_single_timeframe(
                    job_id, timeframe, batch_size, service
                )
                results.append(result)

                if result["status"] == "failed":
                    logger.warning(
                        "Timeframe %s failed for job %s, "
                        "continuing to next timeframe",
                        timeframe,
                        job_id,
                    )

                # タイムフレーム処理後のリソース解放
                logger.info(
                    "Releasing resources after timeframe %s for job %s",
                    timeframe,
                    job_id,
                )
                # 不要な変数を明示的に削除
                del result
                # ガベージコレクションを実行
                gc.collect()
                # イベントループに制御を返す
                await _asyncio.sleep(0.1)

                # リソース解放後の状況を確認
                _log_memory_usage(
                    f"After timeframe {timeframe} cleanup for job {job_id}"
                )

            overall_success = sum(r.get("success_count", 0) for r in results)
            overall_failed = sum(r.get("failed_count", 0) for r in results)

            await repo.mark_completed(
                job_id,
                success_count=overall_success,
                failed_count=overall_failed,
            )
            await _commit_with_rollback(session, "mark_completed", job_id)

            # バッチ処理完了時のリソース状況
            _log_memory_usage(f"Batch job {job_id} completed successfully")

        except Exception:
            logger.exception(
                "process_jpx_all_multi_sequence failed for job %s", job_id
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


async def _execute_single_timeframe(
    job_id: int, timeframe: str, batch_size: int, service: StockPriceService
) -> Dict[str, Any]:
    """単一のタイムフレームでバッチ処理を実行するヘルパー関数.

    Args:
        job_id (int): ジョブID
        timeframe (str): タイムフレーム（1d/1m/1h）
        batch_size (int): バッチサイズ
        service (StockPriceService): 株価収集サービス

    Returns:
        Dict[str, Any]: 実行結果（status, success_count, failed_count等）
    """
    start_time = dt.now()
    result: Dict[str, Any] = {
        "timeframe": timeframe,
        "status": "completed",
        "success_count": 0,
        "failed_count": 0,
        "error_message": None,
        "started_at": start_time.isoformat(),
        "finished_at": None,
    }

    # タイムフレーム処理開始時のリソース状況
    _log_memory_usage(f"Timeframe {timeframe} started for job {job_id}")

    try:
        if service.stock_master_service is None:
            raise ServiceError(message="StockMasterService is required")

        symbols = await service.stock_master_service.get_all_active_symbols()
        total = len(symbols)

        pending_tasks, _progress_callback, _sync_progress_cb = (
            _make_progress_handlers(job_id)
        )

        success = 0
        failed = 0

        async with BatchExecutionContext(
            service.batch_service,
            job_type="jpx_all_multi_sequence",
            params={
                "timeframe": timeframe,
                "batch_size": batch_size,
            },
        ) as ctx:
            for i in range(0, total, batch_size):
                chunk = symbols[i : i + batch_size]
                s_inc, f_inc, _errs = await _process_chunk_multi(
                    chunk, service, timeframe, {}
                )
                success += s_inc
                failed += f_inc

                # チャンク処理ごとにメモリ解放
                del chunk
                del _errs

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

                # 定期的にイベントループに制御を返す
                await _asyncio.sleep(0.01)

        await _await_pending_tasks(
            pending_tasks, "while awaiting pending progress tasks"
        )

        result["success_count"] = success
        result["failed_count"] = failed
        result["finished_at"] = dt.now().isoformat()

        # タイムフレーム処理完了時のリソース状況
        _log_memory_usage(f"Timeframe {timeframe} completed for job {job_id}")

        logger.info(
            "Completed timeframe %s for job %s: success=%s, failed=%s",
            timeframe,
            job_id,
            success,
            failed,
        )

    except Exception as exc:
        logger.exception(
            "Failed to execute timeframe %s for job %s", timeframe, job_id
        )
        result["status"] = "failed"
        result["error_message"] = str(exc)
        result["finished_at"] = dt.now().isoformat()

    return result
