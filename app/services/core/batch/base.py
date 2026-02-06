"""サービス層バッチの基底クラスとコンテキスト.

このモジュールはサービス固有の `batch.py` が継承して使う基底を提供します。
設計方針として本モジュールはサービス固有の型に依存しないようにし、
インターフェース（メソッド名）により疎結合で呼び出せるようにします。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseBatchRunner:
    """サービス層向けバッチランナー基底クラス.

    継承クラスは `run(*args, **kwargs)` を実装して処理サマリ辞書を返してください。
    基底は分割や進捗コールバックのユーティリティを提供します。
    """

    def __init__(
        self,
        batch_service: Any,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """初期化.

        Args:
            batch_service: バッチ実行管理サービス（ジョブコンテキスト等を提供する）
            progress_callback: 進捗更新コールバック（任意）
        """
        if batch_service is None:
            raise ValueError("batch_service is required")

        self.batch_service = batch_service
        self.progress_callback = progress_callback

    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """実行エントリポイント（継承先で実装）."""
        raise NotImplementedError()

    @staticmethod
    def chunk_iter(items: List[Any], size: int) -> Iterable[List[Any]]:
        """アイテムリストを指定サイズで分割するジェネレータ."""
        for i in range(0, len(items), size):
            yield items[i : i + size]

    async def _update_ctx_progress(self, ctx: Any, **kwargs: Any) -> None:
        """コンテキスト（batch job context）へ進捗更新を試みる.

        ctx はサービス側が返すオブジェクトで、`update_progress` を持つことが期待される。
        なければ安全に無視します。
        """
        if not ctx:
            return

        updater = getattr(ctx, "update_progress", None)
        try:
            if callable(updater):
                result = updater(**kwargs)
                # updater が coroutine を返す/実装している場合に await
                if hasattr(result, "__await__"):
                    await result
        except Exception:
            logger.exception("Failed to update batch progress")


class BatchExecutionContext:
    """バッチサービス向けの軽量 async コンテキストマネージャ.

    使用例:
        async with BatchExecutionContext(batch_service, job_type="jpx_all", params={}) as ctx:
            # ctx は batch_service が返すコンテキストオブジェクト（存在すれば）
            await ctx.update_progress(...)

    実装は `batch_service` に存在するメソッド名を動的にチェックして呼び出します。
    これにより core 側は具体的な実装に強く依存しません。
    """

    def __init__(
        self,
        batch_service: Any,
        job_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """コンテキスト初期化.

        Args:
            batch_service: バッチ実行管理サービス
            job_type: ジョブ種別
            params: ジョブパラメータ（任意）
        """
        self.batch_service = batch_service
        self.job_type = job_type
        self.params = params or {}
        self._ctx: Optional[Any] = None

    async def __aenter__(self) -> Optional[Any]:
        """コンテキスト開始時の処理を行い、内部コンテキストを返す.

        優先順位: create_context -> start_job
        """
        # 優先順位: create_context -> start_job
        creator = getattr(self.batch_service, "create_context", None)
        starter = getattr(self.batch_service, "start_job", None)

        try:
            if callable(creator):
                maybe = creator(job_type=self.job_type, params=self.params)
                if hasattr(maybe, "__await__"):
                    self._ctx = await maybe
                else:
                    self._ctx = maybe
            elif callable(starter):
                maybe = starter(job_type=self.job_type, params=self.params)
                if hasattr(maybe, "__await__"):
                    self._ctx = await maybe
                else:
                    self._ctx = maybe
            else:
                self._ctx = None
        except Exception:
            logger.exception("Failed to start batch job context")
            self._ctx = None

        return self._ctx

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """コンテキスト終了時に finish を呼び出す.

        優先順位: ctx.finish -> batch_service.finish_job
        """
        # 優先順位: ctx.finish -> batch_service.finish_job
        try:
            if self._ctx is not None:
                fin = getattr(self._ctx, "finish", None)
                if callable(fin):
                    maybe = fin(
                        success=(exc is None),
                        error=(str(exc) if exc else None),
                    )
                    if hasattr(maybe, "__await__"):
                        await maybe
                    return

            fin_service = getattr(self.batch_service, "finish_job", None)
            if callable(fin_service):
                maybe = fin_service(success=(exc is None), error=(str(exc) if exc else None))
                if hasattr(maybe, "__await__"):
                    await maybe
        except Exception:
            logger.exception("Failed to finish batch job context")
