"""Stock price service (orchestration layer).

Orchestrates fetching, conversion, validation and saving of stock price data.

Notes:
    - Integrates ``Fetcher``, ``Converter``, ``Validator`` and ``Saver``
    - Intended to be used by batch processes and API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, cast

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.business import ServiceError
from app.exceptions.database import RecordNotFoundError
from app.exceptions.external_api import YahooFinanceError
from app.exceptions.validation import FieldValidationError
from app.repositories.market_data.stock_price import (
    StockData1dRepository,
    StockData1hRepository,
    StockData1moRepository,
    StockData1mRepository,
    StockData1wkRepository,
    StockData5mRepository,
    StockData15mRepository,
    StockData30mRepository,
)
from app.schemas.stock_data import StockPriceCreate
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.validator import StockPriceValidator
from app.utils.logger import get_logger

# 時間軸とリポジトリのマッピング（DB読み取り用）
TIMEFRAME_REPOSITORY_MAP = {
    "1m": StockData1mRepository,
    "5m": StockData5mRepository,
    "15m": StockData15mRepository,
    "30m": StockData30mRepository,
    "1h": StockData1hRepository,
    "1d": StockData1dRepository,
    "1wk": StockData1wkRepository,
    "1mo": StockData1moRepository,
}

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.services.data_synchronization.market_data.stock_master.service import (
        StockMasterService,
    )


class StockDataWrapper(NamedTuple):
    """
    株価データラッパー.

    Attributes:
        symbol: 銘柄コード
        timeframe: タイムフレーム
        data: DataFrame形式の株価データ
    """

    symbol: str
    timeframe: str
    data: pd.DataFrame


class StockPriceServiceResult:
    """
    株価データサービス実行結果.

    Attributes:
        success: 全体の成功/失敗
        symbol: 銘柄コード
        timeframe: タイムフレーム
        records_processed: 処理されたレコード数
        records_saved: 保存されたレコード数
        errors: エラーリスト
        warnings: 警告リスト
    """

    def __init__(
        self,
        success: bool,
        symbol: str,
        timeframe: str,
        records_processed: int = 0,
        records_saved: int = 0,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        """結果オブジェクトを初期化する.

        Args:
            success: 成功フラグ
            symbol: 銘柄コード
            timeframe: タイムフレーム
            records_processed: 処理数
            records_saved: 保存数
            errors: エラーリスト
            warnings: 警告リスト
        """
        self.success = success
        self.symbol = symbol
        self.timeframe = timeframe
        self.records_processed = records_processed
        self.records_saved = records_saved
        self.errors = errors or []
        self.warnings = warnings or []


class StockPriceService:
    """
    株価データサービス（オーケストレーション層）.

    Fetcher、Converter、Validator、Saverを統合し、
    株価データ収集の全体フローを管理します。

    Attributes:
        fetcher: 株価データ取得クラス
        saver: 株価データ保存クラス
        converter: データ変換クラス
        validator: データ検証クラス
    """

    def __init__(
        self,
        fetcher: StockPriceFetcher,
        saver: StockPriceSaver,
        converter: StockPriceConverter,
        validator: StockPriceValidator,
        stock_master_service: Optional["StockMasterService"] = None,
    ):
        """
        初期化.

        Args:
            fetcher: StockPriceFetcherインスタンス
            saver: StockPriceSaverインスタンス
            converter: StockPriceConverterインスタンス
            validator: StockPriceValidatorインスタンス
        """
        self.fetcher = fetcher
        self.saver = saver
        self.converter = converter
        self.validator = validator
        self.stock_master_service = stock_master_service

    async def fetch_and_save(
        self,
        symbols: List[str],
        timeframe: str,
        period: Optional[str] = None,
    ) -> List[StockPriceServiceResult]:
        """
        複数銘柄の株価データを順次で取得・保存.

        Args:
            symbols: 銘柄コードリスト
            timeframe: タイムフレーム

        Returns:
            List[StockPriceServiceResult]: 各銘柄の処理結果
        """
        logger.info(
            "Starting batch stock data fetch and save: %d symbols, %s",
            len(symbols),
            timeframe,
        )

        async def process_symbols(symbols_list: List[str]) -> List[StockPriceServiceResult]:
            # 複数銘柄を一括で処理する（fetch_batch を有効活用）
            logger.info(
                "Starting batch stock data fetch and save: %d symbols, %s",
                len(symbols_list),
                timeframe,
            )

            results: List[StockPriceServiceResult] = []

            try:
                # 一度にまとめて取得
                batch_results = await self.fetcher.fetch_batch(
                    symbols=symbols_list, timeframe=timeframe, period=period
                )

                for symbol in symbols_list:
                    try:
                        stock_data_list = batch_results.get(symbol, [])

                        if not stock_data_list:
                            results.append(
                                StockPriceServiceResult(
                                    success=True,
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    records_processed=0,
                                    records_saved=0,
                                    warnings=["No data was retrieved"],
                                )
                            )
                            continue

                        records_processed = len(stock_data_list)
                        pydantic_data = stock_data_list

                        # 簡易検証: 現状バリデータは未作成のため、受け取ったデータをそのまま有効とみなす
                        valid_data = pydantic_data

                        try:
                            records = self.converter.to_saver_records(
                                cast(List[StockPriceCreate], valid_data)
                            )
                        except Exception as e:
                            logger.exception("Failed to convert records for saving")
                            results.append(
                                StockPriceServiceResult(
                                    success=False,
                                    symbol=symbol,
                                    timeframe=timeframe,
                                    records_processed=records_processed,
                                    records_saved=0,
                                    errors=[f"Conversion error: {e}"],
                                )
                            )
                            continue

                        payload = [
                            {
                                "symbol": symbol,
                                "timeframe": timeframe,
                                "records": records,
                            }
                        ]

                        saved_count = await self.saver.save_batch(payload)

                        logger.info(
                            "Successfully processed %s: %d/%d records saved",
                            symbol,
                            saved_count,
                            records_processed,
                        )

                        results.append(
                            StockPriceServiceResult(
                                success=True,
                                symbol=symbol,
                                timeframe=timeframe,
                                records_processed=records_processed,
                                records_saved=saved_count,
                            )
                        )

                    except YahooFinanceError as e:
                        logger.error("Yahoo Finance error for %s: %s", symbol, e)
                        results.append(
                            StockPriceServiceResult(
                                success=False,
                                symbol=symbol,
                                timeframe=timeframe,
                                errors=[f"Yahoo Finance API error: {str(e)}"],
                            )
                        )

                    except Exception as e:
                        logger.exception("Unexpected error processing %s", symbol)
                        results.append(
                            StockPriceServiceResult(
                                success=False,
                                symbol=symbol,
                                timeframe=timeframe,
                                errors=[f"Unexpected error: {str(e)}"],
                            )
                        )

                # ここまでで全銘柄分の upsert はセッション上に積まれている。
                # 一度だけコミットして確定する（失敗時はロールバックして結果を失敗にする）。
                try:
                    await self.saver.session.commit()
                except Exception as commit_err:
                    logger.exception("Commit failed for batch: %s", commit_err)
                    try:
                        await self.saver.session.rollback()
                    except Exception:
                        logger.exception("Rollback after commit failure also failed")
                    # コミット失敗はすべての成功結果を失敗に変換する
                    failed_results: List[StockPriceServiceResult] = []
                    for res in results:
                        if res.success and res.records_saved > 0:
                            failed_results.append(
                                StockPriceServiceResult(
                                    success=False,
                                    symbol=res.symbol,
                                    timeframe=res.timeframe,
                                    records_processed=res.records_processed,
                                    records_saved=0,
                                    errors=[f"Commit failed: {commit_err}"],
                                )
                            )
                        else:
                            failed_results.append(res)
                    return failed_results

                return results

            except Exception:
                # 全体のフェッチ失敗など重大エラーは各銘柄失敗として記録
                logger.exception("Batch fetch failed for symbols: %s", symbols_list)
                return [
                    StockPriceServiceResult(
                        success=False,
                        symbol=symbol,
                        timeframe=timeframe,
                        errors=["Batch fetch failed"],
                    )
                    for symbol in symbols_list
                ]

        # 一括処理（fetch_batch を一度だけ呼ぶ）
        processed_results = await process_symbols(symbols)

        # 集計ログ
        successful = sum(1 for r in processed_results if r.success)
        total_processed = sum(r.records_processed for r in processed_results)
        total_saved = sum(r.records_saved for r in processed_results)

        logger.info(
            "Batch processing completed: %d/%d successful, %d/%d saved",
            successful,
            len(symbols),
            total_saved,
            total_processed,
        )

        return processed_results

    async def fetch_and_save_for_all_jpx(
        self,
        timeframe: str,
        market: Optional[str] = None,
        batch_size: int = 100,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
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
        if not self.stock_master_service:
            raise ServiceError(
                message=("StockMasterService is required for " "fetch_and_save_for_all_jpx")
            )

        start_time = perf_counter()

        # 銘柄リスト取得
        if market:
            symbols = await self.stock_master_service.get_symbols_by_market(market)
        else:
            symbols = await self.stock_master_service.get_all_active_symbols()

        total = len(symbols)
        success = 0
        failed = 0
        errors: List[Dict[str, Any]] = []

        # Run synchronously without job management; update progress via callback only
        for i in range(0, total, batch_size):
            batch = symbols[i : i + batch_size]

            try:
                results = await self.fetch_and_save(batch, timeframe=timeframe, period=period)
            except Exception as exc:
                logger.exception("Batch processing failed for symbols %s", batch)
                for s in batch:
                    failed += 1
                    errors.append({"symbol": s, "errors": [str(exc)]})
                continue

            for res in results:
                if res.success:
                    success += 1
                else:
                    failed += 1
                    errors.append({"symbol": res.symbol, "errors": res.errors})

            if progress_callback:
                try:
                    progress_callback(
                        {
                            "total": total,
                            "processed": success + failed,
                            "success": success,
                            "failed": failed,
                        }
                    )
                except Exception:
                    logger.exception("Progress callback failed")

        elapsed = perf_counter() - start_time

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "errors": errors,
            "elapsed_time": elapsed,
        }

    async def get_stock_data(
        self,
        symbol: str,
        timeframe: str,
        period: Optional[str] = None,
    ) -> Optional[StockDataWrapper]:
        """
        株価データを取得（読み取り専用）.

        Args:
            symbol: 銘柄コード
            timeframe: タイムフレーム

        Returns:
            StockDataWrapper or None: 取得した株価データ
        """
        logger.info(
            "Fetching stock data (read-only): %s, %s",
            symbol,
            timeframe,
        )

        try:
            ##########################################################
            # フェッチ: 読み取り専用のデータ取得（get_stock_data）
            # 単一銘柄でも一括取得インターフェースを利用する
            ##########################################################
            batch_results = await self.fetcher.fetch_batch(
                symbols=[symbol], timeframe=timeframe, period=period
            )
            stock_data_list = batch_results.get(symbol, [])

            # List[StockData] を DataFrame に変換して返す
            if stock_data_list:
                df = pd.DataFrame([item.model_dump() for item in stock_data_list])

                return StockDataWrapper(symbol=symbol, timeframe=timeframe, data=df)
            else:
                return None

        except Exception:
            logger.exception("Error fetching stock data for %s", symbol)
            return None

    async def get_stock_data_from_db(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """DBから株価データを取得して辞書リストで返す.

        Args:
            db: AsyncSession
            symbol: 銘柄コード
            timeframe: 時間軸
            start: 開始日時
            end: 終了日時
            limit: 取得上限
            offset: オフセット

        Returns:
            List[Dict[str, Any]]: レコード辞書のリスト（timestamp を含む場合あり）

        Raises:
            FieldValidationError: timeframe が無効な場合
            RecordNotFoundError: データが見つからない場合
        """
        repo_class = TIMEFRAME_REPOSITORY_MAP.get(timeframe)
        if not repo_class:
            raise FieldValidationError(message=f"Invalid timeframe: {timeframe}")

        repo = repo_class(session=db)  # type: ignore[abstract]

        results = await repo.get_by_symbol_and_range(
            symbol=symbol, start=start, end=end, limit=limit, offset=offset
        )

        if not results:
            raise RecordNotFoundError(message=f"No data found for symbol '{symbol}'")

        rows: List[Dict[str, Any]] = []
        for row in results:
            d: Dict[str, Any] = {
                "symbol": row.symbol,
                "open": float(row.open),
                "high": float(row.high),
                "low": float(row.low),
                "close": float(row.close),
                "volume": row.volume,
            }
            if hasattr(row, "adj_close") and row.adj_close is not None:
                d["adj_close"] = float(row.adj_close)
            if hasattr(row, "timestamp"):
                d["timestamp"] = row.timestamp
            rows.append(d)

        return rows

    async def delete_all_for_timeframe(self, db: AsyncSession, timeframe: str) -> int:
        """指定時間軸の全データを削除して削除件数を返す.

        Args:
            db: AsyncSession
            timeframe: 時間軸

        Returns:
            int: 削除件数
        """
        repo_class = TIMEFRAME_REPOSITORY_MAP.get(timeframe)
        if not repo_class:
            raise FieldValidationError(message=f"Invalid timeframe: {timeframe}")

        repo = repo_class(session=db)  # type: ignore[abstract]

        try:
            deleted_count = await repo.delete_all()
            await db.commit()
            return deleted_count
        except Exception as e:
            await db.rollback()
            raise ServiceError(message=f"Failed to delete data: {e}") from e
