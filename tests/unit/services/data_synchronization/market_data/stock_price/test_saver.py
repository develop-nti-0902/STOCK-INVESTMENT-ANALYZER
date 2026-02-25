"""`StockPriceSaver` の単体テスト（書き直し）.

テストは日本語コメントで記載し、外部依存（Repository）はモック化して
`StockPriceSaver` のデータ変換・保存フローを検証します.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.exceptions.validation import FieldValidationError
from app.services.data_synchronization.market_data.stock_price.saver import StockPriceSaver


def make_mock_repo():
    """Generate a simple mock repository with `upsert_bulk` AsyncMock."""
    repo = AsyncMock()
    repo.upsert_bulk = AsyncMock(return_value=1)
    return repo


class TestStockPriceSaver:
    """Unit tests for `StockPriceSaver` repository selection and conversion."""

    @pytest.fixture
    def patched_repos(self):
        """Patch timeframe repository factories to return mock repos for tests."""
        factories = {
            k: (lambda session, _k=k: make_mock_repo())
            for k in [
                "1m",
                "5m",
                "15m",
                "30m",
                "1h",
                "1d",
                "1wk",
                "1mo",
            ]
        }
        with patch.dict(
            "app.services.data_synchronization.market_data.stock_price.saver.StockPriceSaver.TIMEFRAME_REPOSITORIES",
            factories,
            clear=False,
        ):
            yield

    @pytest.fixture
    def mock_session(self):
        """Provide an AsyncMock session for saver tests."""
        return AsyncMock()

    @pytest.fixture
    def saver(self, patched_repos, mock_session):
        """Return a `StockPriceSaver` instance configured with patched repos."""
        return StockPriceSaver(mock_session, batch_size=100, max_concurrent_batches=5)

    def test_init_creates_repositories(self, saver):
        """Initialization creates repository entries for expected timeframes."""
        expected = ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"]
        for k in expected:
            assert k in saver.repositories

    def test_select_repository(self, saver):
        """Selecting a valid timeframe returns a repository; invalid returns None."""
        repo = saver._select_repository("1d")
        assert repo is not None
        assert saver._select_repository("bogus") is None

    def test_convert_dataframe_to_db_records_basic(self, saver):
        """Convert a basic DataFrame to DB records with localized timestamps."""
        df = pd.DataFrame(
            {
                "timestamp": ["2023-01-01 09:00:00"],
                "open": [100.0],
                "high": [105.0],
                "low": [95.0],
                "close": [102.0],
                "volume": [1000],
            }
        )

        records = saver._convert_dataframe_to_db_records("7203", df)
        assert len(records) == 1
        r = records[0]
        assert r["symbol"] == "7203"
        assert isinstance(r["timestamp"], datetime)
        assert r["open"] == 100.0

    def test_convert_dataframe_missing_columns(self, saver):
        """Missing required columns raise FieldValidationError."""
        df = pd.DataFrame({"timestamp": ["2023-01-01"], "open": [100.0]})
        with pytest.raises(FieldValidationError, match="Missing required columns"):
            saver._convert_dataframe_to_db_records("7203", df)

    def test_convert_dataframe_skips_invalid_rows(self, saver):
        """Rows containing NaN values are skipped during conversion."""
        df = pd.DataFrame(
            {
                "timestamp": ["2023-01-01", "2023-01-01"],
                "open": [100.0, None],
                "high": [105.0, 106.0],
                "low": [95.0, 96.0],
                "close": [102.0, 103.0],
                "volume": [1000, 1100],
            }
        )
        records = saver._convert_dataframe_to_db_records("7203", df)
        assert len(records) == 1

    def test_convert_dataframe_price_logic_violation(self, saver):
        """Logically inconsistent price rows (high < low) are skipped."""
        df = pd.DataFrame(
            {
                "timestamp": ["2023-01-01"],
                "open": [100.0],
                "high": [90.0],
                "low": [95.0],
                "close": [92.0],
                "volume": [1000],
            }
        )
        records = saver._convert_dataframe_to_db_records("7203", df)
        assert records == []

    def test_convert_dict_list_to_db_records_basic(self, saver):
        """Convert a list of dict records into DB-ready records."""
        data = [
            {
                "timestamp": "2023-01-01 09:00:00",
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": 102.0,
                "volume": 1000,
            }
        ]
        records = saver._convert_dict_list_to_db_records("7203", data)
        assert len(records) == 1
        assert records[0]["symbol"] == "7203"

    def test_prepare_data_for_db_invalid_type(self, saver):
        """Unsupported input types for `_prepare_data_for_db` raise FieldValidationError."""
        with pytest.raises(FieldValidationError, match="Unsupported data type"):
            saver._prepare_data_for_db("7203", "bad")

    @pytest.mark.asyncio
    async def test__save_symbol_uses_repository_upsert(self, saver):
        """`_save_symbol` calls repository `upsert_bulk` when saving records."""
        mock_repo = AsyncMock()
        mock_repo.upsert_bulk = AsyncMock(return_value=2)
        saver.repositories["1d"] = mock_repo

        # データは辞書リストで渡す
        data = {
            "1d": [
                {
                    "timestamp": "2023-01-01",
                    "open": 100.0,
                    "high": 105.0,
                    "low": 95.0,
                    "close": 102.0,
                    "volume": 1000,
                }
            ]
        }

        res = await saver._save_symbol("7203", data)
        assert res["1d"] == 2
        mock_repo.upsert_bulk.assert_awaited()

    @pytest.mark.asyncio
    async def test_save_batch_aggregates_results(self, saver):
        """`save_batch` aggregates results returned by `_save_symbol`."""
        saver._save_symbol = AsyncMock(return_value={"1d": 1})

        data_list = [
            {
                "symbol": "7203",
                "timeframe": "1d",
                "records": [
                    {
                        "timestamp": "2023-01-01",
                        "open": 1,
                        "high": 2,
                        "low": 1,
                        "close": 2,
                        "volume": 1,
                    }
                ],
            }
        ]

        total = await saver.save_batch(data_list)
        # 上で返した dict の合計値が返ること
        assert total == 1
