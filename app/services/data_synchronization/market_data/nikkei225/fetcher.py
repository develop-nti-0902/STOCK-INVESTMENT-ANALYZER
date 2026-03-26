"""日経225データ取得モジュール.

yfinance を使用して ^N225 日足データを取得します。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

from app.exceptions.external_api import YahooFinanceError
from app.services.data_synchronization._core.fetchers.retry_mixin import RetryMixin
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Nikkei225Fetcher(RetryMixin):
    """yfinance から ^N225 日足データを取得するクラス."""

    SYMBOL = "^N225"
    INTERVAL = "1d"

    async def fetch(self, max_period: Optional[int] = None) -> pd.DataFrame:
        """日経225データを取得する.

        Args:
            max_period: 取得日数上限。
                None  → 全利用可能データを取得（yfinance デフォルト最大期間）。
                N > 0 → start = today - N 日, end = today で期間指定取得。

        Returns:
            pd.DataFrame: yfinance の DataFrame（index = DatetimeIndex）.
                カラム: Open, High, Low, Close, Adj Close, Volume

        Raises:
            ValueError: max_period が 0 以下の場合。
            YahooFinanceError: yfinance API エラー。
        """
        if max_period is not None and max_period <= 0:
            raise ValueError(f"max_period must be positive, got {max_period}")

        loop = asyncio.get_event_loop()

        try:
            if max_period is None:
                raw = await loop.run_in_executor(
                    None,
                    lambda: yf.download(
                        self.SYMBOL,
                        interval=self.INTERVAL,
                        progress=False,
                        auto_adjust=False,
                    ),
                )
            else:
                start_date = (datetime.now(tz=timezone.utc) - timedelta(days=max_period)).date()
                raw = await loop.run_in_executor(
                    None,
                    lambda: yf.download(
                        self.SYMBOL,
                        start=str(start_date),
                        interval=self.INTERVAL,
                        progress=False,
                        auto_adjust=False,
                    ),
                )
        except Exception as exc:
            raise YahooFinanceError(
                message=f"Failed to fetch data for {self.SYMBOL}: {exc}"
            ) from exc

        if raw is None or raw.empty:
            logger.warning("No data returned from yfinance for %s", self.SYMBOL)
            return pd.DataFrame()

        logger.info(
            "Fetched %d rows for %s (max_period=%s)",
            len(raw),
            self.SYMBOL,
            max_period,
        )
        return raw
