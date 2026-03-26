"""`Nikkei225Fetcher` の単体テスト.

yfinance をモックし、引数の組み合わせ・エラーハンドリング・
MultiIndex フラット化などの挙動を検証します。
"""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from app.exceptions.external_api import YahooFinanceError
from app.services.data_synchronization.market_data.nikkei225.fetcher import Nikkei225Fetcher

# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_simple_df() -> pd.DataFrame:
    """シンプルな単レベル列の DataFrame を返す."""
    return pd.DataFrame(
        {
            "Open": [27000.0],
            "High": [27500.0],
            "Low": [26500.0],
            "Close": [27200.0],
            "Adj Close": [27200.0],
            "Volume": [100_000],
        },
        index=pd.to_datetime(["2024-01-04"]),
    )


def _make_multiindex_df() -> pd.DataFrame:
    """yfinance が返す可能性がある MultiIndex 列を持つ DataFrame を返す."""
    tuples = [
        ("Open", "^N225"),
        ("High", "^N225"),
        ("Low", "^N225"),
        ("Close", "^N225"),
        ("Adj Close", "^N225"),
        ("Volume", "^N225"),
    ]
    cols = pd.MultiIndex.from_tuples(tuples)
    df = pd.DataFrame(
        [[27000.0, 27500.0, 26500.0, 27200.0, 27200.0, 100_000]],
        index=pd.to_datetime(["2024-01-04"]),
        columns=cols,
    )
    return df


# ---------------------------------------------------------------------------
# テストクラス
# ---------------------------------------------------------------------------


class TestNikkei225FetcherValidation:
    """入力バリデーションのテスト."""

    @pytest.mark.asyncio
    async def test_max_period_zero_raises_value_error(self):
        """max_period=0 は ValueError を発生させる."""
        fetcher = Nikkei225Fetcher()
        with pytest.raises(ValueError, match="max_period must be positive"):
            await fetcher.fetch(max_period=0)

    @pytest.mark.asyncio
    async def test_max_period_negative_raises_value_error(self):
        """max_period=-1 は ValueError を発生させる."""
        fetcher = Nikkei225Fetcher()
        with pytest.raises(ValueError, match="max_period must be positive"):
            await fetcher.fetch(max_period=-1)


class TestNikkei225FetcherCallArgs:
    """yf.download への呼び出し引数のテスト."""

    @pytest.mark.asyncio
    async def test_max_period_none_calls_without_start(self):
        """max_period=None のとき yf.download に start 引数が渡されないこと."""
        fetcher = Nikkei225Fetcher()
        simple_df = _make_simple_df()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=simple_df,
        ) as mock_download:
            result = await fetcher.fetch(max_period=None)

        call_kwargs = mock_download.call_args
        # start 引数が渡されていないこと
        assert "start" not in (call_kwargs.kwargs or {})
        # period 引数も渡されていないこと（指定なしで yfinance がデフォルト最大を返す）
        assert "period" not in (call_kwargs.kwargs or {})
        assert not result.empty

    @pytest.mark.asyncio
    async def test_max_period_30_calls_with_start(self):
        """max_period=30 のとき yf.download に start 引数（文字列）が渡されること."""
        fetcher = Nikkei225Fetcher()
        simple_df = _make_simple_df()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=simple_df,
        ) as mock_download:
            result = await fetcher.fetch(max_period=30)

        call_kwargs = mock_download.call_args
        # start が日付文字列として渡されていること
        assert "start" in (call_kwargs.kwargs or {})
        assert isinstance(call_kwargs.kwargs["start"], str)
        assert not result.empty

    @pytest.mark.asyncio
    async def test_symbol_is_n225(self):
        """^N225 シンボルを第1引数として yf.download が呼ばれること."""
        fetcher = Nikkei225Fetcher()
        simple_df = _make_simple_df()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=simple_df,
        ) as mock_download:
            await fetcher.fetch(max_period=None)

        positional = mock_download.call_args.args
        assert positional[0] == "^N225"

    @pytest.mark.asyncio
    async def test_interval_is_1d(self):
        """interval='1d' が yf.download に渡されること."""
        fetcher = Nikkei225Fetcher()
        simple_df = _make_simple_df()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=simple_df,
        ) as mock_download:
            await fetcher.fetch(max_period=None)

        call_kwargs = mock_download.call_args.kwargs
        assert call_kwargs.get("interval") == "1d"


class TestNikkei225FetcherReturnValues:
    """戻り値・例外のテスト."""

    @pytest.mark.asyncio
    async def test_returns_dataframe_on_success(self):
        """正常系: DataFrame が返ること."""
        fetcher = Nikkei225Fetcher()
        simple_df = _make_simple_df()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=simple_df,
        ):
            result = await fetcher.fetch()

        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    @pytest.mark.asyncio
    async def test_returns_empty_dataframe_when_yfinance_returns_empty(self):
        """yfinance が空 DataFrame を返した場合、空 DataFrame が返ること."""
        fetcher = Nikkei225Fetcher()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=pd.DataFrame(),
        ):
            result = await fetcher.fetch()

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_yfinance_exception_raises_yahoo_finance_error(self):
        """yfinance が例外を投げた場合、YahooFinanceError にラップされること."""
        fetcher = Nikkei225Fetcher()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            side_effect=Exception("network error"),
        ):
            with pytest.raises(YahooFinanceError):
                await fetcher.fetch()

    @pytest.mark.asyncio
    async def test_multiindex_columns_returned_as_is(self):
        """yfinance が MultiIndex DataFrame を返しても、Fetcher はそのまま返すこと.

        フラット化は Converter の責務であるため、Fetcher は加工しない。
        """
        fetcher = Nikkei225Fetcher()
        mi_df = _make_multiindex_df()

        with patch(
            "app.services.data_synchronization.market_data.nikkei225.fetcher.yf.download",
            return_value=mi_df,
        ):
            result = await fetcher.fetch()

        assert isinstance(result, pd.DataFrame)
        assert not result.empty
