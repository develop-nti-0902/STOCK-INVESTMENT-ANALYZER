"""
株価データサービス（オーケストレーション層）

データ取得（Fetcher）と保存（Saver）を統合し、株価データ収集の全体フローを管理します。
仕様書: docs/architecture/layers/service_layer.md 3.2.4章
"""

import asyncio
from datetime import date, datetime
from typing import List, NamedTuple, Optional, Union, cast

import pandas as pd

from app.exceptions.business import StockDataValidationError
from app.exceptions.external_api import YahooFinanceError
from app.services.market_data.stock_price.converter import StockPriceConverter
from app.services.market_data.stock_price.fetcher import StockPriceFetcher
from app.services.market_data.stock_price.saver import StockPriceSaver
from app.services.market_data.stock_price.validator import StockPriceValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
        max_concurrent: int = 5,
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
        self.fetcher = fetcher
        self.saver = saver
        self.converter = converter
        self.validator = validator
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

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
            dict_data = [item.model_dump() for item in valid_data]
            saved_count = await self.saver.save_batch(dict_data)

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
