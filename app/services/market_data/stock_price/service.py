"""Stock price service (orchestration layer).

Orchestrates fetching, conversion, validation and saving of stock price data.

Notes:
    - Integrates ``Fetcher``, ``Converter``, ``Validator`` and ``Saver``
    - Intended to be used by batch processes and API endpoints.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from time import perf_counter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Union,
    cast,
)

import pandas as pd

from app.exceptions.business import ServiceError, StockDataValidationError
from app.exceptions.external_api import YahooFinanceError
from app.exceptions.validation import FieldValidationError
from app.schemas.stock_data import StockPriceCreate
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.validator import StockPriceValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.services.batch.batch_execution_service import (
        BatchExecutionService,
    )
    from app.services.market_data.stock_master.service import (
        StockMasterService,
    )


class StockDataWrapper(NamedTuple):
    """
    株価データラッパー

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
    株価データサービス実行結果

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
        self.success = success
        self.symbol = symbol
        self.timeframe = timeframe
        self.records_processed = records_processed
        self.records_saved = records_saved
        self.errors = errors or []
        self.warnings = warnings or []


class StockPriceService:
    """
    株価データサービス（オーケストレーション層）

    Fetcher、Converter、Validator、Saverを統合し、
    株価データ収集の全体フローを管理します。

    Attributes:
        fetcher: 株価データ取得クラス
        saver: 株価データ保存クラス
        converter: データ変換クラス
        validator: データ検証クラス
        max_concurrent: 最大並列処理数
    """

    def __init__(
        self,
        fetcher: StockPriceFetcher,
        saver: StockPriceSaver,
        converter: StockPriceConverter,
        validator: StockPriceValidator,
        batch_service: "BatchExecutionService",
        max_concurrent: int = 5,
        stock_master_service: Optional["StockMasterService"] = None,
    ):
        """
        初期化

        Args:
            fetcher: StockPriceFetcherインスタンス
            saver: StockPriceSaverインスタンス
            converter: StockPriceConverterインスタンス
            validator: StockPriceValidatorインスタンス
            max_concurrent: 最大並列処理数
        """
        # バッチ実行管理サービスは必須（Noneは許容しない）
        if batch_service is None:
            raise FieldValidationError(
                message="batch_service is required and cannot be None"
            )

        self.fetcher = fetcher
        self.saver = saver
        self.converter = converter
        self.validator = validator
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        # 銘柄マスタサービス（オプション）。依存性注入によって渡される想定
        self.stock_master_service = stock_master_service
        # バッチ実行管理サービス（必須）
        self.batch_service = batch_service

    def _normalize_date_param(
        self, d: Union[date, datetime, str, None]
    ) -> Optional[date]:
        """
        start_date/end_date パラメータを Optional[date] に正規化します。
        - datetime -> date
        - date -> date
        - ISO 形式の文字列 -> date (失敗時は None)
        - None -> None
        """
        if d is None:
            return None
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, date):
            return d
        if isinstance(d, str):
            try:
                return date.fromisoformat(d)
            except Exception:
                try:
                    return datetime.fromisoformat(d).date()
                except Exception:
                    return None
        return None

    async def fetch_and_save_single(
        self,
        symbol: str,
        timeframe: str,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str],
    ) -> StockPriceServiceResult:
        """
        単一銘柄の株価データを取得・変換・検証・保存

        Args:
            symbol: 銘柄コード
            timeframe: タイムフレーム
            start_date: 開始日
            end_date: 終了日

        Returns:
            StockPriceServiceResult: 処理結果
        """
        logger.info(
            f"Starting single stock data fetch and save: {symbol}, {timeframe}"
        )

        try:
            # 1. データ取得
            start_param = self._normalize_date_param(start_date)
            end_param = self._normalize_date_param(end_date)

            stock_data_list = await self.fetcher.fetch_single(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_param,
                end_date=end_param,
            )

            if not stock_data_list:
                return StockPriceServiceResult(
                    success=True,
                    symbol=symbol,
                    timeframe=timeframe,
                    records_processed=0,
                    records_saved=0,
                    warnings=["No data was retrieved"],
                )

            records_processed = len(stock_data_list)

            # List[StockData] を直接使用（fetcherが既にPydanticモデルを返す）
            pydantic_data = stock_data_list

            # 3. データ検証
            validation_results = []
            for item in pydantic_data:
                result = self.validator.validate(item)
                validation_results.append(result)
                if not result.is_valid:
                    logger.warning(
                        f"Validation failed for {symbol}: {result.errors}"
                    )

            # 検証失敗のデータを除外
            valid_data = [
                data
                for data, result in zip(pydantic_data, validation_results)
                if result.is_valid
            ]

            if not valid_data:
                return StockPriceServiceResult(
                    success=False,
                    symbol=symbol,
                    timeframe=timeframe,
                    records_processed=records_processed,
                    records_saved=0,
                    errors=["All data failed validation"],
                )

            # 4. データ保存
            # Pydanticモデルのフィールド名 (trade_date, open_price, ...) を
            # Saver が期待する DB 形式 (timestamp, open, ...) にマッピングして渡す
            # Pydanticモデル -> Saverが期待する辞書形式へ変換
            try:
                records = self.converter.to_saver_records(
                    cast(List[StockPriceCreate], valid_data)
                )
            except Exception as e:
                logger.exception("Failed to convert records for saving")
                return StockPriceServiceResult(
                    success=False,
                    symbol=symbol,
                    timeframe=timeframe,
                    records_processed=records_processed,
                    records_saved=0,
                    errors=[f"Conversion error: {e}"],
                )

            payload = [
                {"symbol": symbol, "timeframe": timeframe, "records": records}
            ]
            saved_count = await self.saver.save_batch(payload)

            logger.info(
                "Successfully processed %s: %d/%d records saved",
                symbol,
                saved_count,
                records_processed,
            )

            return StockPriceServiceResult(
                success=True,
                symbol=symbol,
                timeframe=timeframe,
                records_processed=records_processed,
                records_saved=saved_count,
            )

        except YahooFinanceError as e:
            logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return StockPriceServiceResult(
                success=False,
                symbol=symbol,
                timeframe=timeframe,
                errors=[f"Yahoo Finance API error: {str(e)}"],
            )

        except StockDataValidationError as e:
            logger.error(f"Validation error for {symbol}: {e}")
            return StockPriceServiceResult(
                success=False,
                symbol=symbol,
                timeframe=timeframe,
                errors=[f"Data validation error: {str(e)}"],
            )

        except Exception as e:
            logger.exception(f"Unexpected error processing {symbol}")
            return StockPriceServiceResult(
                success=False,
                symbol=symbol,
                timeframe=timeframe,
                errors=[f"Unexpected error: {str(e)}"],
            )

    async def fetch_and_save_multiple(
        self,
        symbols: List[str],
        timeframe: str,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str],
    ) -> List[StockPriceServiceResult]:
        """
        複数銘柄の株価データを並列で取得・保存

        Args:
            symbols: 銘柄コードリスト
            timeframe: タイムフレーム
            start_date: 開始日
            end_date: 終了日

        Returns:
            List[StockPriceServiceResult]: 各銘柄の処理結果
        """
        logger.info(
            "Starting batch stock data fetch and save: %d symbols, %s",
            len(symbols),
            timeframe,
        )

        async def process_symbol(symbol: str) -> StockPriceServiceResult:
            async with self._semaphore:
                return await self.fetch_and_save_single(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                )

        # 並列処理
        tasks = [process_symbol(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 例外処理
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                symbol = symbols[i]
                logger.error(f"Exception processing {symbol}: {result}")
                processed_results.append(
                    StockPriceServiceResult(
                        success=False,
                        symbol=symbol,
                        timeframe=timeframe,
                        errors=["Exception occurred during processing"],
                    )
                )
            else:
                processed_results.append(cast(StockPriceServiceResult, result))

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

    async def fetch_all_jpx_stocks(
        self,
        timeframe: str,
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str],
        market: Optional[str] = None,
        max_concurrent: int = 20,
        batch_size: int = 100,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        JPX全銘柄を対象に一括で株価データを収集する

        Args:
            timeframe: タイムフレーム
            start_date: 開始日
            end_date: 終了日
            market: 市場フィルタ（省略可）
            max_concurrent: 並列実行数（セマフォ）
            batch_size: バッチ内の銘柄数
            progress_callback: 進捗コールバック（辞書を受け取る）

        Returns:
            処理サマリ辞書
        """
        if not self.stock_master_service:
            raise ServiceError(
                message=(
                    "StockMasterService is required for "
                    "fetch_all_jpx_stocks"
                )
            )

        start_time = perf_counter()

        # 銘柄リスト取得
        if market:
            symbols = await self.stock_master_service.get_symbols_by_market(
                market
            )
        else:
            symbols = await self.stock_master_service.get_all_active_symbols()

        total = len(symbols)
        success = 0
        failed = 0
        errors: List[Dict[str, Any]] = []

        from app.services.batch.batch_execution_service import (
            BatchExecutionContext,
        )

        async with BatchExecutionContext(
            self.batch_service,
            job_type="jpx_all",
            params={"timeframe": timeframe, "market": market},
        ) as ctx:
            # バッチ分割
            for i in range(0, total, batch_size):
                batch = symbols[i : i + batch_size]

                sem = asyncio.Semaphore(max_concurrent)

                async def _process(symbol: str):
                    try:
                        async with sem:
                            result = await self.fetch_and_save_single(
                                symbol=symbol,
                                timeframe=timeframe,
                                start_date=start_date,
                                end_date=end_date,
                            )
                            return result
                    except Exception as exc:  # pylint: disable=broad-except
                        return StockPriceServiceResult(
                            success=False,
                            symbol=symbol,
                            timeframe=timeframe,
                            errors=[str(exc)],
                        )

                tasks = [_process(s) for s in batch]
                # 並列実行して結果を収集
                batch_results = await asyncio.gather(
                    *tasks, return_exceptions=True
                )

                # gather 後に集計して競合状態を回避
                for res in batch_results:
                    if isinstance(res, Exception):
                        failed += 1
                        errors.append(
                            {"symbol": "unknown", "errors": [str(res)]}
                        )
                    else:
                        # 型は StockPriceServiceResult に絞る
                        result = cast(StockPriceServiceResult, res)
                        if result.success:
                            success += 1
                        else:
                            failed += 1
                            errors.append(
                                {
                                    "symbol": result.symbol,
                                    "errors": result.errors,
                                }
                            )

                # 進捗通知
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

                # バッチサービスへ進捗を保存
                try:
                    await ctx.update_progress(
                        processed=success + failed,
                        total=total,
                        success=success,
                        failed=failed,
                    )
                except Exception:
                    logger.exception("Failed to update batch progress")

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
        start_date: Union[date, datetime, str],
        end_date: Union[date, datetime, str],
    ) -> Optional[StockDataWrapper]:
        """
        株価データを取得（読み取り専用）

        Args:
            symbol: 銘柄コード
            timeframe: タイムフレーム
            start_date: 開始日
            end_date: 終了日

        Returns:
            StockDataWrapper or None: 取得した株価データ
        """
        logger.info(f"Fetching stock data (read-only): {symbol}, {timeframe}")

        try:
            start_param = self._normalize_date_param(start_date)
            end_param = self._normalize_date_param(end_date)

            stock_data_list = await self.fetcher.fetch_single(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_param,
                end_date=end_param,
            )

            # List[StockData] を DataFrame に変換して返す
            if stock_data_list:
                df = pd.DataFrame(
                    [item.model_dump() for item in stock_data_list]
                )

                return StockDataWrapper(
                    symbol=symbol, timeframe=timeframe, data=df
                )
            else:
                return None

        except Exception:
            logger.exception(f"Error fetching stock data for {symbol}")
            return None
