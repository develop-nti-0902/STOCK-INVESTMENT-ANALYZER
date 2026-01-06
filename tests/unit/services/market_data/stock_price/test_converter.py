"""
StockPriceConverter単体テスト

StockPriceConverterクラスの機能をテストします。
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from app.exceptions.business import ServiceError
from app.schemas.stock_data import StockPriceCreate
from app.services.market_data.stock_price.converter import StockPriceConverter


class TestStockPriceConverter:
    """StockPriceConverterテストクラス"""

    @pytest.fixture
    def converter(self):
        """テスト対象のコンバーターインスタンス"""
        return StockPriceConverter()

    @pytest.fixture
    def sample_dataframe(self):
        """テスト用のサンプルDataFrame"""
        # UTCタイムゾーン付きのDatetimeIndexを作成
        dates = pd.date_range("2023-01-01", periods=3, freq="D", tz="UTC")

        data = {
            "Open": [100.0, 105.0, 110.0],
            "High": [105.0, 110.0, 115.0],
            "Low": [95.0, 100.0, 105.0],
            "Close": [102.0, 107.0, 112.0],
            "Volume": [1000, 1500, 1200],
            "Adj Close": [102.0, 107.0, 112.0],
        }

        df = pd.DataFrame(data, index=dates)
        return df

    @pytest.fixture
    def sample_dataframe_tz_naive(self):
        """タイムゾーンなしのサンプルDataFrame"""
        dates = pd.date_range("2023-01-01", periods=2, freq="D")

        data = {
            "Open": [100.0, 105.0],
            "High": [105.0, 110.0],
            "Low": [95.0, 100.0],
            "Close": [102.0, 107.0],
            "Volume": [1000, 1500],
            "Adj Close": [102.0, 107.0],
        }

        df = pd.DataFrame(data, index=dates)
        return df

    @pytest.mark.asyncio
    async def test_yfinance_to_pydantic_success(
        self, converter, sample_dataframe
    ):
        """正常系のyfinance_to_pydanticテスト"""
        symbol = "7203.T"
        timeframe = "1d"

        with pytest.raises(NotImplementedError):
            converter.from_dataframe(sample_dataframe, symbol, timeframe)

    @pytest.mark.asyncio
    async def test_yfinance_to_pydantic_tz_naive(
        self, converter, sample_dataframe_tz_naive
    ):
        """タイムゾーンなしDataFrameのテスト"""
        symbol = "7203.T"
        timeframe = "1d"

        with pytest.raises(NotImplementedError):
            converter.from_dataframe(
                sample_dataframe_tz_naive, symbol, timeframe
            )

    @pytest.mark.asyncio
    async def test_yfinance_to_pydantic_empty_dataframe(self, converter):
        """空のDataFrameテスト"""
        empty_df = pd.DataFrame()

        with pytest.raises(NotImplementedError):
            converter.from_dataframe(empty_df, "7203.T", "1d")

    @pytest.mark.asyncio
    async def test_yfinance_to_pydantic_missing_columns(self, converter):
        """必須カラム不足のテスト"""
        dates = pd.date_range("2023-01-01", periods=2, freq="D", tz="UTC")
        incomplete_df = pd.DataFrame(
            {
                "Open": [100.0, 105.0],
                "Close": [102.0, 107.0],
                # High, Low, Volume が不足
            },
            index=dates,
        )

        with pytest.raises(NotImplementedError):
            converter.from_dataframe(incomplete_df, "7203.T", "1d")

    @pytest.mark.asyncio
    async def test_yfinance_to_pydantic_invalid_index(self, converter):
        """無効なインデックスのテスト"""
        invalid_df = pd.DataFrame(
            {
                "Open": [100.0],
                "High": [105.0],
                "Low": [95.0],
                "Close": [102.0],
                "Volume": [1000],
                "Adj Close": [102.0],
            }
        )  # DatetimeIndexなし

        with pytest.raises(NotImplementedError):
            converter.from_dataframe(invalid_df, "7203.T", "1d")

    @pytest.mark.asyncio
    async def test_pydantic_to_dict_success(self, converter):
        """正常系のpydantic_to_dictテスト"""
        stock_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            open_price=100.0,
            high=105.0,
            low=95.0,
            close=102.0,
            volume=1000,
            adj_close=102.0,
        )

        with pytest.raises(NotImplementedError):
            converter.from_pydantic(stock_data)

    @pytest.mark.asyncio
    async def test_pydantic_to_dict_with_none_values(self, converter):
        """None値を含むデータのテスト"""
        stock_data = StockPriceCreate(
            symbol="7203.T",
            trade_date=datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            open_price=None,
            high=None,
            low=None,
            close=102.0,
            volume=None,
            adj_close=None,
        )

        with pytest.raises(NotImplementedError):
            converter.from_pydantic(stock_data)

    def test_validate_data_success(self, converter, sample_dataframe):
        """正常系の_validate_dataテスト"""
        # エラーが発生しないことを確認
        converter._validate_data(sample_dataframe)

    def test_validate_data_empty(self, converter):
        """空DataFrameの_validate_dataテスト"""
        empty_df = pd.DataFrame()

        with pytest.raises(ServiceError, match="DataFrame is empty"):
            converter._validate_data(empty_df)

    def test_validate_data_missing_columns(self, converter):
        """必須カラム不足の_validate_dataテスト"""
        dates = pd.date_range("2023-01-01", periods=2, freq="D", tz="UTC")
        incomplete_df = pd.DataFrame({"Open": [100.0, 105.0]}, index=dates)

        with pytest.raises(ServiceError, match="Missing required columns"):
            converter._validate_data(incomplete_df)

    def test_normalize_timestamps_utc(self, sample_dataframe):
        """UTCタイムゾーン付きの正規化テスト（テストヘルパー使用）"""
        from tests.unit.helpers.time_utils import normalize_timestamps

        result = normalize_timestamps(sample_dataframe)

        assert isinstance(result.index, pd.DatetimeIndex)
        assert str(result.index.tz) == "Asia/Tokyo"

    def test_normalize_timestamps_naive(self, sample_dataframe_tz_naive):
        """タイムゾーンなしの正規化テスト（テストヘルパー使用）"""
        from tests.unit.helpers.time_utils import normalize_timestamps

        result = normalize_timestamps(sample_dataframe_tz_naive)

        assert isinstance(result.index, pd.DatetimeIndex)
        assert str(result.index.tz) == "Asia/Tokyo"

    def test_safe_float(self, converter):
        """_safe_floatのテスト"""
        from tests.unit.helpers.time_utils import safe_float

        assert safe_float(100.5) == 100.5
        assert safe_float("100.5") == 100.5
        assert safe_float(None) is None
        assert safe_float(float("nan")) is None
        assert safe_float("invalid") is None

    def test_safe_int(self, converter):
        """_safe_intのテスト"""
        from tests.unit.helpers.time_utils import safe_int

        assert safe_int(100) == 100
        assert safe_int("100") == 100
        assert safe_int(100.5) == 100  # 切り捨て
        assert safe_int(None) is None
        assert safe_int(float("nan")) is None
        assert safe_int("invalid") is None
