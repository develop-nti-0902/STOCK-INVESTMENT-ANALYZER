"""Stock price batch runner.

このモジュールは `StockPriceService` の全銘柄バッチ処理を担当します。
`BaseBatchRunner` を継承し、ジョブ管理には
`app.services.batch.batch_execution_service.BatchExecutionContext` を利用して
`BatchExecution` テーブルへ記録します。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from app.services.data_synchronization._core.batch import BaseBatchRunner
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.services.market_data.stock_master.service import StockMasterService
    from app.services.market_data.stock_price.service import StockPriceService


class StockPriceBatchRunner(BaseBatchRunner):
    """JPX 全銘柄向けのバッチランナー.

    コンストラクタでは `batch_service` と `stock_price_service` を注入します。
    """

    def __init__(
        self,
        stock_price_service: "StockPriceService",
        stock_master_service: "StockMasterService",
    ) -> None:
        """初期化.

        Args:
            stock_price_service: 株価サービス
            stock_master_service: 銘柄マスタサービス
        """
        super().__init__()
        # `batch_service` は廃止済だが、mypy が属性参照を検出する箇所があるため
        # 互換性のために None を設定しておく（外部で参照されても安全）。
        self.batch_service: Optional[Any] = None
        self.stock_price_service = stock_price_service
        self.stock_master_service = stock_master_service

    async def execute_jpx_all_for_timeframe(
        self,
        timeframe: str,
        market: Optional[str] = None,
        batch_size: int = 100,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        JPX全銘柄を対象に一括で株価データを収集する.

        Args:
            timeframe: タイムフレーム
            market: 市場フィルタ（省略可）
            batch_size: バッチ内の銘柄数
            progress_callback: 進捗コールバック（辞書を受け取る）

        Returns:
            処理サマリ辞書
        """
        # バッチサービス（BatchExecutionService）のコンテキストを利用
        try:
            from app.services.batch.batch_execution_service import BatchExecutionContext
        except Exception:
            from contextlib import asynccontextmanager

            @asynccontextmanager
            async def BatchExecutionContext(batch_service, job_type, params=None):
                yield None

        if not self.stock_master_service:
            raise RuntimeError("stock_master_service is required for batch run")

        ##########################################################
        # 銘柄リスト取得
        ##########################################################
        if market:
            symbols = await self.stock_master_service.get_symbols_by_market(market)
        else:
            symbols = await self.stock_master_service.get_all_active_symbols()

        total = len(symbols)
        success = 0
        failed = 0
        errors: List[Dict[str, Any]] = []

        ##########################################################
        # バッチコンテキスト開始 / 初期化
        ##########################################################
        async with BatchExecutionContext(
            self.batch_service,
            job_type="jpx_all",
            params={"timeframe": timeframe, "market": market},
        ) as ctx:
            ##########################################################
            # バッチ分割・順次処理
            ##########################################################
            processed = 0
            for chunk in self.chunk_iter(list(symbols), batch_size):
                try:
                    ##########################################################
                    # 保存: Saver に渡してデータベースへ永続化（チャンク単位）
                    ##########################################################
                    results = await self.stock_price_service.fetch_and_save(
                        chunk, timeframe=timeframe, period=period
                    )

                    for res in results:
                        # res は StockPriceServiceResult
                        if res is None:
                            success += 1
                        elif res.success:
                            success += 1
                        else:
                            failed += 1
                            errors.append(
                                {"symbol": res.symbol, "errors": (res.errors or ["Unknown error"])}
                            )

                except Exception as exc:
                    # チャンク全体が例外で失敗した場合は、チャンク内の全銘柄を失敗扱いにする
                    for s in chunk:
                        failed += 1
                        errors.append({"symbol": s, "errors": [str(exc)]})

                processed += len(chunk)

                ##########################################################
                # 進捗更新: バッチ管理テーブルへ反映
                ##########################################################
                try:
                    if ctx is not None:
                        await ctx.update_progress(
                            processed=processed,
                            total=total,
                            success=success,
                            failed=failed,
                        )
                except Exception:
                    logger.exception("Failed to update batch progress via context")

        ##########################################################
        # 結果集計 / 終了処理
        ##########################################################
        elapsed = None

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors,
            "elapsed_time": elapsed,
        }
