"""`Nikkei225Converter` の単体テスト.

DataFrame → Pydantic スキーマ変換・MultiIndex フラット化・
タイムゾーン変換・欠損値処理を検証します。
"""

from __future__ import annotations

from datetime import timezone

import numpy as np
import pandas as pd
import pytest

from app.schemas.market_data.nikkei225 import Nikkei2251dCreate
from app.services.data_synchronization.market_data.nikkei225.converter import Nikkei225Converter

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def converter() -> Nikkei225Converter:
    """テスト対象インスタンスを返す."""
    return Nikkei225Converter()


def _simple_df(has_adj_close: bool = True) -> pd.DataFrame:
    """テスト用の単レベル列 DataFrame を生成する."""
    data: dict = {
        "Open": [27000.0, 27100.0],
        "High": [27500.0, 27600.0],
        "Low": [26500.0, 26600.0],
        "Close": [27200.0, 27300.0],
        "Volume": [100_000, 200_000],
    }
    if has_adj_close:
        data["Adj Close"] = [27200.0, 27300.0]
    return pd.DataFrame(data, index=pd.to_datetime(["2024-01-04", "2024-01-05"]))


def _multiindex_df() -> pd.DataFrame:
    """yfinance が返す MultiIndex 列を持つ DataFrame を生成する."""
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
# テスト
# ---------------------------------------------------------------------------


class TestNikkei225ConverterFromDataframe:
    """from_dataframe メソッドのテスト."""

    def test_empty_dataframe_returns_empty_list(self, converter: Nikkei225Converter):
        """空 DataFrame は空リストを返す."""
        result = converter.from_dataframe(pd.DataFrame())
        assert result == []

    def test_normal_dataframe_returns_correct_count(self, converter: Nikkei225Converter):
        """正常な DataFrame から正しい件数のスキーマが生成される."""
        df = _simple_df()
        result = converter.from_dataframe(df)
        assert len(result) == 2
        assert all(isinstance(r, Nikkei2251dCreate) for r in result)

    def test_ohlcv_values_are_correct(self, converter: Nikkei225Converter):
        """OHLCV 値が正確に変換されること."""
        df = _simple_df()
        result = converter.from_dataframe(df)
        assert result[0].open == 27000.0
        assert result[0].high == 27500.0
        assert result[0].low == 26500.0
        assert result[0].close == 27200.0
        assert result[0].volume == 100_000

    def test_adj_close_present_is_set(self, converter: Nikkei225Converter):
        """Adj Close 列が存在する場合、adj_close が None でないこと."""
        df = _simple_df(has_adj_close=True)
        result = converter.from_dataframe(df)
        assert result[0].adj_close is not None
        assert result[0].adj_close == 27200.0

    def test_adj_close_absent_is_none(self, converter: Nikkei225Converter):
        """Adj Close 列が存在しない場合、adj_close が None であること."""
        df = _simple_df(has_adj_close=False)
        result = converter.from_dataframe(df)
        assert result[0].adj_close is None

    def test_adj_close_nan_is_none(self, converter: Nikkei225Converter):
        """Adj Close が NaN の場合、adj_close が None であること."""
        df = _simple_df(has_adj_close=True)
        df["Adj Close"] = np.nan
        result = converter.from_dataframe(df)
        assert result[0].adj_close is None

    def test_nan_ohlc_row_is_skipped(self, converter: Nikkei225Converter):
        """OHLC が NaN の行はスキップされること."""
        df = _simple_df()
        df.loc[df.index[0], "Open"] = np.nan
        result = converter.from_dataframe(df)
        # 2行のうち1行がスキップされる
        assert len(result) == 1

    def test_all_nan_ohlc_returns_empty_list(self, converter: Nikkei225Converter):
        """全行の OHLC が NaN の場合は空リストが返ること."""
        df = _simple_df()
        df["Open"] = np.nan
        result = converter.from_dataframe(df)
        assert result == []

    def test_multiindex_columns_are_flattened(self, converter: Nikkei225Converter):
        """MultiIndex 列がフラット化されて正常変換されること."""
        df = _multiindex_df()
        result = converter.from_dataframe(df)
        assert len(result) == 1
        assert result[0].open == 27000.0
        assert result[0].close == 27200.0


class TestNikkei225ConverterTimezone:
    """タイムゾーン変換のテスト."""

    def test_timezone_naive_index_is_converted_to_jst(self, converter: Nikkei225Converter):
        """timezone-naive インデックスは UTC→JST 変換されること."""
        df = _simple_df()
        # インデックスを timezone-naive にする
        df.index = df.index.tz_localize(None)
        result = converter.from_dataframe(df)
        ts = result[0].timestamp
        assert ts.tzinfo is not None
        # JST は UTC+9
        assert ts.utcoffset().total_seconds() == 9 * 3600

    def test_timezone_aware_index_is_converted_to_jst(self, converter: Nikkei225Converter):
        """timezone-aware インデックスは JST に変換されること."""
        df = _simple_df()
        df.index = df.index.tz_localize("UTC")
        result = converter.from_dataframe(df)
        ts = result[0].timestamp
        assert ts.tzinfo is not None
        assert ts.utcoffset().total_seconds() == 9 * 3600

    def test_already_jst_index_stays_jst(self, converter: Nikkei225Converter):
        """既に JST の場合も JST のまま返ること."""
        df = _simple_df()
        df.index = df.index.tz_localize("Asia/Tokyo")
        result = converter.from_dataframe(df)
        ts = result[0].timestamp
        assert ts.utcoffset().total_seconds() == 9 * 3600


class TestNikkei225ConverterToSaverRecords:
    """to_saver_records メソッドのテスト."""

    def test_to_saver_records_returns_list_of_dicts(self, converter: Nikkei225Converter):
        """Pydantic モデルリストが辞書リストに変換されること."""
        from datetime import datetime

        models = [
            Nikkei2251dCreate(
                timestamp=datetime(2024, 1, 4, tzinfo=timezone.utc),
                open=27000.0,
                high=27500.0,
                low=26500.0,
                close=27200.0,
                adj_close=27200.0,
                volume=100_000,
            )
        ]
        records = converter.to_saver_records(models)
        assert isinstance(records, list)
        assert len(records) == 1
        assert isinstance(records[0], dict)
        assert records[0]["open"] == 27000.0

    def test_to_saver_records_empty_list(self, converter: Nikkei225Converter):
        """空リストを渡すと空リストが返ること."""
        result = converter.to_saver_records([])
        assert result == []

    def test_to_saver_records_all_fields_included(self, converter: Nikkei225Converter):
        """変換辞書に timestamp, open, high, low, close, adj_close, volume が含まれること."""
        from datetime import datetime

        model = Nikkei2251dCreate(
            timestamp=datetime(2024, 1, 4, tzinfo=timezone.utc),
            open=27000.0,
            high=27500.0,
            low=26500.0,
            close=27200.0,
            adj_close=None,
            volume=0,
        )
        record = converter.to_saver_records([model])[0]
        for key in ("timestamp", "open", "high", "low", "close", "adj_close", "volume"):
            assert key in record
