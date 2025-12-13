"""
株価データ取得クラス

Yahoo Finance API (yfinance) を使用して株価データを取得します。
仕様書: docs/architecture/layers/service_layer.md 3.2.1章
"""

import asyncio
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf
from pydantic import ValidationError

from app.exceptions.external_api import YahooFinanceError
from app.schemas.market_data.stock_price import StockData
from app.services.core.fetchers.retry_mixin import RetryMixin
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimeframeMapping:
    """タイムフレームマッピング"""

    MAPPINGS = {
        "1m": "1m",  # 1分足
        "5m": "5m",  # 5分足
        "15m": "15m",  # 15分足
        "30m": "30m",  # 30分足
        "1h": "1h",  # 1時間足
        "1d": "1d",  # 1日足
        "1wk": "1wk",  # 1週足
        "1mo": "1mo",  # 1月足
    }

    # 各タイムフレームの最大取得期間（日数）
    # maxの場合は全期間を意味する
    MAX_PERIODS = {
        "1m": 7,  # 過去7日間
        "5m": 30,  # 過去30日間（Yahoo Financeの制限に合わせて短く設定）
        "15m": 30,  # 過去30日間（Yahoo Financeの制限に合わせて短く設定）
        "30m": 30,  # 過去30日間（Yahoo Financeの制限に合わせて短く設定）
        "1h": 365,  # 過去365日間（約1年、Yahoo Financeの制限に合わせて短く設定）
        "1d": "max",  # 全期間
        "1wk": "max",  # 全期間
        "1mo": "max",  # 全期間
    }

    # yfinanceのperiodパラメータマッピング
    PERIOD_MAPPINGS = {
        "1m": None,  # period使用せずstart/endを使用
        "5m": None,  # period使用せずstart/endを使用
        "15m": None,  # period使用せずstart/endを使用
        "30m": None,  # period使用せずstart/endを使用
        "1h": None,  # period使用せずstart/endを使用
        "1d": "max",  # 全期間
        "1wk": "max",  # 全期間
        "1mo": "max",  # 全期間
    }

    @classmethod
    def get_yfinance_interval(cls, timeframe: str) -> str:
        """タイムフレームをyfinanceのintervalに変換"""
        if timeframe not in cls.MAPPINGS:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return cls.MAPPINGS[timeframe]

    @classmethod
    def get_supported_timeframes(cls) -> List[str]:
        """サポートされているタイムフレームのリストを取得"""
        return list(cls.MAPPINGS.keys())

    @classmethod
    def get_period(cls, timeframe: str) -> Optional[str]:
        """
        指定されたタイムフレームのyfinance periodパラメータを取得します。

        Args:
            timeframe: タイムフレーム

        Returns:
            Optional[str]: periodパラメータ（使用しない場合はNone）
        """
        if timeframe not in cls.PERIOD_MAPPINGS:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        return cls.PERIOD_MAPPINGS[timeframe]

    @classmethod
    def get_max_period_dates(
        cls, timeframe: str
    ) -> Tuple[Optional[date], Optional[date]]:
        """
        指定されたタイムフレームの最大期間の日付範囲を取得します。

        Args:
            timeframe: タイムフレーム

        Returns:
            Tuple[Optional[date], Optional[date]]: (start_date, end_date)
            - start_date: 開始日（maxの場合はNone）
            - end_date: 終了日（常にNoneで今日を意味する）
        """
        if timeframe not in cls.MAX_PERIODS:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        max_period = cls.MAX_PERIODS[timeframe]

        if max_period == "max":
            # 全期間の場合はstart_dateをNoneに
            return None, None
        else:
            # 指定日数分の期間
            end_date = date.today()
            start_date = end_date - timedelta(days=max_period)
            return start_date, None


class StockPriceFetcher(RetryMixin):
    """
    Yahoo Finance APIを使用した株価データ取得クラス

    単一銘柄取得と複数銘柄並列取得に対応し、
    8種類のタイムフレームをサポートします。

    Attributes:
        semaphore: 並列処理数制限用のセマフォ
        max_concurrent_requests: 最大並列リクエスト数
    """

    def __init__(self) -> None:
        """StockPriceFetcherを初期化します。"""
        RetryMixin.__init__(self)

        config = get_settings()
        # 設定から並列数を読み込み（デフォルト10）
        self.max_concurrent_requests = getattr(
            config, "YAHOO_FINANCE_CONCURRENCY_LIMIT", 10
        )
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    async def fetch(self, identifier: str, **kwargs) -> List[StockData]:
        """
        単一銘柄の株価データを取得します。

        Args:
            identifier: 銘柄コード（例: "7203.T"）
            **kwargs: 追加パラメータ（timeframe, start_date, end_date）

        Returns:
            List[StockData]: 株価データのリスト

        Raises:
            ValueError: パラメータが不正な場合
            YahooFinanceError: APIエラーが発生した場合
        """
        # kwargsからパラメータを取得
        timeframe = kwargs.get("timeframe", "1d")
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")

        # パラメータ検証
        if not identifier or not isinstance(identifier, str):
            raise ValueError("Identifier must be a non-empty string")

        try:
            yfinance_interval = TimeframeMapping.get_yfinance_interval(
                timeframe
            )
        except ValueError as e:
            raise ValueError(f"Invalid timeframe: {timeframe}") from e

        # リトライ付きでデータ取得
        return await self._retry_async(
            lambda: self._fetch_single_symbol(
                identifier, yfinance_interval, start_date, end_date, timeframe
            ),
            "fetch_single",
        )

    async def fetch_single(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs,
    ) -> List[StockData]:
        """
        単一銘柄の株価データを取得します。

        Args:
            symbol: 銘柄コード（例: "7203.T"）
            timeframe: タイムフレーム
                ("1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"）
            start_date: 開始日（指定なしの場合は最大期間）
            end_date: 終了日（指定なしの場合は今日）
            **kwargs: 追加パラメータ

        Returns:
            List[StockData]: 株価データのリスト

        Raises:
            ValueError: パラメータが不正な場合
            YahooFinanceError: APIエラーが発生した場合
        """
        # パラメータ検証
        if not symbol or not isinstance(symbol, str):
            raise ValueError("Symbol must be a non-empty string")

        try:
            yfinance_interval = TimeframeMapping.get_yfinance_interval(
                timeframe
            )
        except ValueError as e:
            raise ValueError(f"Invalid timeframe: {timeframe}") from e

        # start_dateとend_dateが指定されていない場合は最大期間を設定
        if start_date is None and end_date is None:
            start_date, end_date = TimeframeMapping.get_max_period_dates(
                timeframe
            )
            logger.debug(
                f"Max period dates for {timeframe}: "
                f"start={start_date}, end={end_date}"
            )

        # リトライ付きでデータ取得
        return await self._retry_async(
            lambda: self._fetch_single_symbol(
                symbol, yfinance_interval, start_date, end_date, timeframe
            ),
            "fetch_single",
        )

    async def fetch_batch(
        self,
        symbols: List[str],
        timeframe: str = "1d",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        **kwargs,
    ) -> Dict[str, List[StockData]]:
        """
        複数銘柄の株価データを並列取得します。

        Args:
            symbols: 銘柄コードのリスト
            timeframe: タイムフレーム
            start_date: 開始日（指定なしの場合は最大期間）
            end_date: 終了日（指定なしの場合は今日）
            **kwargs: 追加パラメータ

        Returns:
            Dict[str, List[StockData]]: 銘柄コードをキーとした株価データ辞書

        Raises:
            ValueError: パラメータが不正な場合
        """
        if not symbols or not isinstance(symbols, list):
            raise ValueError("Symbols must be a non-empty list")

        # start_dateとend_dateが指定されていない場合は最大期間を設定
        if start_date is None and end_date is None:
            start_date, end_date = TimeframeMapping.get_max_period_dates(
                timeframe
            )

        # 各銘柄の取得タスクを作成
        tasks = []
        for symbol in symbols:
            task = self.fetch_single(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                **kwargs,
            )
            tasks.append(task)

        # 並列実行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 結果を辞書にまとめる
        result_dict: Dict[str, List[StockData]] = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch data for {symbol}: {result}")
                result_dict[symbol] = []
            else:
                # result is List[StockData] here
                result_dict[symbol] = result  # type: ignore[assignment]

        return result_dict

    async def _fetch_single_symbol(
        self,
        symbol: str,
        interval: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeframe: Optional[str] = None,
    ) -> List[StockData]:
        """
        単一銘柄のデータをyfinanceから取得します。

        Args:
            symbol: 銘柄コード
            interval: yfinance interval
            start_date: 開始日
            end_date: 終了日
            timeframe: タイムフレーム（period判定用）

        Returns:
            List[StockData]: 株価データのリスト

        Raises:
            YahooFinanceError: APIエラーが発生した場合
        """
        async with self.semaphore:  # 並列数制限
            try:
                # yfinanceの同期APIを非同期で実行
                loop = asyncio.get_event_loop()
                ticker = await loop.run_in_executor(
                    None, lambda: yf.Ticker(symbol)
                )

                # データ取得
                # periodパラメータを使用するか判定
                period = None
                if timeframe:
                    try:
                        period = TimeframeMapping.get_period(timeframe)
                    except ValueError:
                        pass  # 無視してstart/endを使用

                if period:
                    # periodを使用する場合
                    logger.debug(
                        f"Fetching data for {symbol}: period={period}, "
                        f"interval={interval}"
                    )
                    hist = await loop.run_in_executor(
                        None,
                        lambda: ticker.history(
                            period=period,
                            interval=interval,
                            prepost=False,  # 取引時間外データを除外
                            actions=False,  # 配当・分割情報を除外
                        ),
                    )
                else:
                    # start/endを使用する場合
                    logger.debug(
                        f"Fetching data for {symbol}: interval={interval}, "
                        f"start={start_date}, end={end_date}"
                    )
                    hist = await loop.run_in_executor(
                        None,
                        lambda: ticker.history(
                            interval=interval,
                            start=start_date,
                            end=end_date,
                            prepost=False,  # 取引時間外データを除外
                            actions=False,  # 配当・分割情報を除外
                        ),
                    )

                if hist.empty:
                    logger.warning(f"No data found for symbol: {symbol}")
                    return []

                # DataFrameをStockDataリストに変換
                return self._parse_yfinance_data(hist, symbol)

            except Exception as e:
                error_msg = f"Failed to fetch data for {symbol}: {str(e)}"
                logger.error(error_msg)
                raise YahooFinanceError(message=error_msg) from e

    def _parse_yfinance_data(
        self, data: pd.DataFrame, symbol: str
    ) -> List[StockData]:
        """
        yfinanceのDataFrameをStockDataリストに変換します。

        Args:
            data: yfinanceから取得したDataFrame
            symbol: 銘柄コード

        Returns:
            List[StockData]: 株価データのリスト

        Raises:
            ValidationError: データ変換に失敗した場合
        """
        stock_data_list = []

        for index, row in data.iterrows():
            try:
                stock_data = StockData(
                    symbol=symbol,
                    trade_date=index.date(),  # Timestampをdateに変換
                    open_price=(
                        float(row["Open"]) if pd.notna(row["Open"]) else None
                    ),
                    high=float(row["High"]) if pd.notna(row["High"]) else None,
                    low=float(row["Low"]) if pd.notna(row["Low"]) else None,
                    close=(
                        float(row["Close"]) if pd.notna(row["Close"]) else None
                    ),
                    volume=(
                        int(row["Volume"]) if pd.notna(row["Volume"]) else None
                    ),
                    adj_close=(
                        float(row["Adj Close"])
                        if "Adj Close" in row and pd.notna(row["Adj Close"])
                        else None
                    ),
                )
                stock_data_list.append(stock_data)

            except (ValueError, ValidationError) as e:
                logger.warning(
                    f"Failed to parse data for {symbol} on {index.date()}: {e}"
                )
                continue  # 個別のデータ変換失敗はスキップ

        return stock_data_list

    async def validate_identifier(self, symbol: str) -> bool:
        """
        銘柄コードの検証を行います。

        Args:
            symbol: 検証対象の銘柄コード

        Returns:
            bool: 銘柄コードが有効な場合True
        """
        if not symbol or not isinstance(symbol, str):
            return False

        # 基本的なフォーマットチェック（例: 7203.T, AAPL）
        # より詳細な検証は必要に応じて追加
        return len(symbol.strip()) > 0

    async def handle_fetch_error(self, symbol: str, error: Exception) -> None:
        """
        データ取得エラーのハンドリングを行います。

        Args:
            symbol: エラーが発生した銘柄コード
            error: 発生した例外
        """
        logger.error(f"Error fetching data for {symbol}: {error}")

        # Yahoo Finance特有のエラーハンドリング
        if isinstance(error, YahooFinanceError):
            # APIレート制限などの場合の特別処理
            logger.warning(f"Yahoo Finance API error for {symbol}: {error}")
        else:
            # その他のエラー
            logger.error(f"Unexpected error for {symbol}: {error}")
