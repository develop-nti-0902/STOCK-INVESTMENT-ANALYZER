"""Yahoo Finance を利用した株価データ取得モジュール.

yfinance をラップして株価データを取得・整形する機能を提供します.

Notes:
        - 取得は同期的な yfinance API をスレッド実行で非同期に扱います。
            ただし内部は「一括ダウンロード（Tickers.history等）→銘柄ごとの直列パース」
            の設計であり、銘柄ごとの細かい並列化を行う実装ではありません。
        - タイムフレームごとの取得制約やフォールバック処理を含みます。
"""

import asyncio
import re
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
from pydantic import ValidationError

from app.exceptions.external_api import YahooFinanceError
from app.exceptions.validation import FieldValidationError
from app.schemas.market_data.stock_price import StockData
from app.services.core.fetchers.retry_mixin import RetryMixin
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimeframeMapping:
    """タイムフレームマッピング."""

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

    # yfinanceのperiodパラメータマッピング
    PERIOD_MAPPINGS = {
        "1m": "7d",  # period使用せずstart/endを使用
        "5m": "30d",  # period使用せずstart/endを使用
        "15m": "30d",  # period使用せずstart/endを使用
        "30m": "30d",  # period使用せずstart/endを使用
        "1h": "365d",  # period使用せずstart/endを使用
        "1d": "max",  # 全期間
        "1wk": "max",  # 全期間
        "1mo": "max",  # 全期間
    }

    @classmethod
    def get_yfinance_interval(cls, timeframe: str) -> str:
        """タイムフレームをyfinanceのintervalに変換."""
        if timeframe not in cls.MAPPINGS:
            raise FieldValidationError(message=f"Unsupported timeframe: {timeframe}")
        return cls.MAPPINGS[timeframe]

    @classmethod
    def get_supported_timeframes(cls) -> List[str]:
        """サポートされているタイムフレームのリストを取得."""
        return list(cls.MAPPINGS.keys())

    @classmethod
    def get_period(cls, timeframe: str) -> Optional[str]:
        """
        指定されたタイムフレームのyfinance periodパラメータを取得します.

        Args:
            timeframe: タイムフレーム

        Returns:
            Optional[str]: periodパラメータ（使用しない場合はNone）
        """
        if timeframe not in cls.PERIOD_MAPPINGS:
            raise FieldValidationError(message=f"Unsupported timeframe: {timeframe}")

        return cls.PERIOD_MAPPINGS[timeframe]


class StockPriceFetcher(RetryMixin):
    """
    Yahoo Finance APIを使用した株価データ取得クラス.

    単一銘柄取得と複数銘柄の一括取得（非同期で扱う）が可能で、
    8種類のタイムフレームをサポートします。

    Attributes:
        semaphore: 並列処理数制限用のセマフォ
        max_concurrent_requests: 最大並列リクエスト数
    """

    def __init__(self) -> None:
        """StockPriceFetcherを初期化します."""
        RetryMixin.__init__(self)

        config = get_settings()
        # 設定から並列数を読み込み（デフォルト10）
        self.max_concurrent_requests = getattr(config, "YAHOO_FINANCE_CONCURRENCY_LIMIT", 10)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

    async def fetch_batch(
        self,
        symbols: List[str],
        timeframe: str = "1d",
        period: Optional[str] = None,
    ) -> Dict[str, List[StockData]]:
        """
        複数銘柄を一括でダウンロードして非同期に扱います.

        実装は yfinance の一括ダウンロード機能を利用して一度にデータを取得し、
        取得後に銘柄ごとに直列でパースします。内部では同期的な yfinance 呼び出しを
        `run_in_executor` でスレッド実行しているためイベントループを塞ぎませんが、
        銘柄ごとの個別並列実行を行う実装ではない点に注意してください。

        Args:
            symbols: 銘柄コードのリスト
            timeframe: タイムフレーム

        Returns:
            Dict[str, List[StockData]]: 銘柄コードをキーとした株価データ辞書

        Raises:
            ValueError: パラメータが不正な場合
        """
        if not symbols or not isinstance(symbols, list):
            raise FieldValidationError(message="Symbols must be a non-empty list")

        # fetch_batch は複数銘柄一括取得の責務を持つため、
        # 一括最適化処理である内部メソッド `_fetch_multi_symbol` に
        # 委譲して一元化する。
        return await self._retry_async(
            lambda: self._fetch_multi_symbol(symbols, timeframe, period),
            "fetch_batch",
        )

    async def _fetch_multi_symbol(
        self,
        symbols: List[str],
        timeframe: str = "1d",
        period: Optional[str] = None,
    ) -> Dict[str, List[StockData]]:
        """
        内部用: 複数銘柄を yfinance の一括ダウンロードで取得する実装.

        `fetch_multi_yfinance` の実ロジックをこちらに移し、`fetch_batch`
        からもこのメソッドを使うことで責務を一元化します。
        """
        if not symbols or not isinstance(symbols, list):
            raise FieldValidationError(message="Symbols must be a non-empty list")

        try:
            interval = TimeframeMapping.get_yfinance_interval(timeframe)
        except FieldValidationError as e:
            raise FieldValidationError(message=f"Invalid timeframe: {timeframe}") from e

        yf_symbols: List[str] = []
        yf_to_orig: Dict[str, str] = {}
        for s in symbols:
            if isinstance(s, str) and re.fullmatch(r"\d+", s):
                if "." in s:
                    raise FieldValidationError(
                        message=("Japanese stock symbol must be provided " "without suffix '.T'")
                    )
                yf_s = f"{s}.T"
            else:
                yf_s = s
            yf_symbols.append(yf_s)
            yf_to_orig[yf_s] = s

        async with self.semaphore:
            loop = asyncio.get_event_loop()
            try:
                tickers_str = " ".join(yf_symbols)
                tickers_obj = await loop.run_in_executor(None, lambda: yf.Tickers(tickers_str))

                # 引数 period があればそれを優先、なければ timeframe から mapping を取得
                if period is None:
                    try:
                        effective_period = TimeframeMapping.get_period(timeframe)
                    except FieldValidationError:
                        effective_period = None
                else:
                    effective_period = period

                if effective_period:
                    hist = await loop.run_in_executor(
                        None,
                        lambda: tickers_obj.history(
                            period=effective_period,
                            interval=interval,
                            prepost=False,
                            actions=False,
                        ),
                    )
                else:
                    hist = await loop.run_in_executor(
                        None,
                        lambda: tickers_obj.history(
                            interval=interval,
                            prepost=False,
                            actions=False,
                        ),
                    )

                if hist.empty:
                    logger.warning("No data found for requested symbols (initial)")
                    try:
                        hist = await loop.run_in_executor(
                            None,
                            lambda: tickers_obj.history(
                                period="5y",
                                interval=interval,
                                prepost=False,
                                actions=False,
                            ),
                        )
                    except Exception:
                        logger.debug("Fallback fetch failed for multi-symbol request")

                    if hist.empty:
                        return {s: [] for s in symbols}

                results: Dict[str, List[StockData]] = {}

                for yf_s in yf_symbols:
                    orig = yf_to_orig.get(yf_s, yf_s)
                    try:
                        # MultiIndex (attribute, ticker) から当該ティッカー部分を切り出す
                        if isinstance(hist.columns, pd.MultiIndex):
                            try:
                                df_sym = hist.xs(yf_s, axis=1, level=1, drop_level=True)
                            except Exception:
                                cols = [c for c in hist.columns if len(c) > 1 and c[1] == yf_s]
                                if not cols:
                                    results[orig] = []
                                    continue
                                df_sym = hist.loc[:, cols]
                                df_sym.columns = [c[0] for c in cols]
                        else:
                            # 単一銘柄または yfinance の戻りが既に単一インデックスの場合
                            df_sym = hist.copy()

                        parsed = self._parse_yfinance_data(df_sym, orig)
                        results[orig] = parsed
                    except Exception as e:
                        logger.exception("Failed to parse multi data for %s: %s", yf_s, e)
                        results[orig] = []

                return results

            except Exception as e:
                msg = "Failed to fetch multiple symbols due to an internal error."
                logger.exception(msg)
                raise YahooFinanceError(message=msg) from e

    def _parse_yfinance_data(self, data: pd.DataFrame, symbol: str) -> List[StockData]:
        """
        yfinanceのDataFrameをStockDataリストに変換します.

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
                    # intraday の場合は時刻情報を保持する
                    timestamp=index.to_pydatetime(),
                    open_price=(float(row["Open"]) if pd.notna(row["Open"]) else None),
                    high=float(row["High"]) if pd.notna(row["High"]) else None,
                    low=float(row["Low"]) if pd.notna(row["Low"]) else None,
                    close=(float(row["Close"]) if pd.notna(row["Close"]) else None),
                    volume=(int(row["Volume"]) if pd.notna(row["Volume"]) else None),
                    adj_close=(
                        float(row["Adj Close"])
                        if "Adj Close" in row and pd.notna(row["Adj Close"])
                        else None
                    ),
                )
                stock_data_list.append(stock_data)

            except (ValueError, ValidationError) as e:
                logger.warning(
                    "Failed to parse data for %s on %s: %s",
                    symbol,
                    index.date(),
                    e,
                )
                continue  # 個別のデータ変換失敗はスキップ

        return stock_data_list

    async def is_valid_symbol_format(self, symbol: str) -> bool:
        """
        銘柄コードのフォーマット検証を行います.

        Args:
            symbol: 検証対象の銘柄コード

        Returns:
            bool: 銘柄コードが有効なフォーマットの場合True
        """
        if not symbol or not isinstance(symbol, str):
            return False

        # 銘柄コードのフォーマットチェック
        # 例: 7203.T, AAPL, 0001.HK など
        # 英数字で始まり、オプションでドットと取引所接尾辞
        pattern = r"^[A-Z0-9]+(\.[A-Z]+)?$"
        return bool(re.match(pattern, symbol.strip()))

    async def handle_fetch_error(self, symbol: str, error: Exception) -> None:
        """
        データ取得エラーのハンドリングを行います.

        Args:
            symbol: エラーが発生した銘柄コード
            error: 発生した例外
        """
        logger.error("Error fetching data for %s: %s", symbol, error)

        # Yahoo Finance特有のエラーハンドリング
        if isinstance(error, YahooFinanceError):
            # APIレート制限などの場合の特別処理
            logger.warning("Yahoo Finance API error for %s: %s", symbol, error)
        else:
            # その他のエラー
            logger.error("Unexpected error for %s: %s", symbol, error)
