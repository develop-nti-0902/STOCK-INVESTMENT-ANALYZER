"""`Nikkei225Service` の単体テスト.

Fetcher/Converter/Validator/Saver をモックし、
4層フローの結合・エラーハンドリングを検証します。
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from app.exceptions.external_api import YahooFinanceError
from app.schemas.market_data.nikkei225 import Nikkei2251dCreate
from app.services.data_synchronization.market_data.nikkei225.converter import Nikkei225Converter
from app.services.data_synchronization.market_data.nikkei225.fetcher import Nikkei225Fetcher
from app.services.data_synchronization.market_data.nikkei225.saver import Nikkei225Saver
from app.services.data_synchronization.market_data.nikkei225.service import (
    Nikkei225Service,
    Nikkei225ServiceResult,
)
from app.services.data_synchronization.market_data.nikkei225.validator import Nikkei225Validator

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


def _make_service() -> tuple[
    Nikkei225Service,
    MagicMock,  # fetcher
    MagicMock,  # converter
    MagicMock,  # validator
    MagicMock,  # saver
]:
    """モック依存を持つ Nikkei225Service インスタンスを返す."""
    fetcher = MagicMock(spec=Nikkei225Fetcher)
    converter = MagicMock(spec=Nikkei225Converter)
    validator = MagicMock(spec=Nikkei225Validator)
    saver = MagicMock(spec=Nikkei225Saver)

    service = Nikkei225Service(
        fetcher=fetcher,
        converter=converter,
        validator=validator,
        saver=saver,
    )
    return service, fetcher, converter, validator, saver


def _make_schema(n: int = 2) -> list[Nikkei2251dCreate]:
    """テスト用 Nikkei2251dCreate リストを生成する."""
    return [
        Nikkei2251dCreate(
            timestamp=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
            open=27000.0 + i,
            high=27500.0 + i,
            low=26500.0 + i,
            close=27200.0 + i,
            adj_close=27200.0 + i,
            volume=100_000 + i,
        )
        for i in range(n)
    ]


def _make_valid_result() -> MagicMock:
    """バリデーション成功の ValidationResult モックを返す."""
    v = MagicMock()
    v.is_valid = True
    v.errors = []
    v.warnings = []
    return v


def _make_invalid_result(errors: list[str] | None = None) -> MagicMock:
    """バリデーション失敗の ValidationResult モックを返す."""
    v = MagicMock()
    v.is_valid = False
    v.errors = errors or ["Validation failed"]
    v.warnings = []
    return v


# ---------------------------------------------------------------------------
# テスト
# ---------------------------------------------------------------------------


class TestNikkei225ServiceFetchAndSaveSuccess:
    """正常フローのテスト."""

    @pytest.mark.asyncio
    async def test_success_result_has_correct_counts(self):
        """正常完了時、records_fetched と records_saved が正しいこと."""
        service, fetcher, converter, validator, saver = _make_service()

        df = pd.DataFrame({"Open": [1.0]})
        fetcher.fetch = AsyncMock(return_value=df)

        schemas = _make_schema(3)
        converter.from_dataframe = MagicMock(return_value=schemas)
        validator.validate = MagicMock(return_value=_make_valid_result())
        converter.to_saver_records = MagicMock(return_value=[s.model_dump() for s in schemas])
        saver.save = AsyncMock(return_value=3)

        result = await service.fetch_and_save(max_period=30)

        assert isinstance(result, Nikkei225ServiceResult)
        assert result.success is True
        assert result.records_fetched == 3
        assert result.records_saved == 3
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_layers_called_in_order(self):
        """Fetcher→Converter→Validator→Saver の順で呼ばれること."""
        service, fetcher, converter, validator, saver = _make_service()

        call_order: list[str] = []

        df = pd.DataFrame({"Open": [1.0]})

        async def mock_fetch(max_period=None):
            call_order.append("fetcher")
            return df

        def mock_from_df(d):
            call_order.append("converter.from_dataframe")
            return _make_schema(1)

        def mock_validate(d):
            call_order.append("validator")
            return _make_valid_result()

        def mock_to_records(models):
            call_order.append("converter.to_saver_records")
            return [m.model_dump() for m in models]

        async def mock_save(records):
            call_order.append("saver")
            return len(records)

        fetcher.fetch = mock_fetch
        converter.from_dataframe = mock_from_df
        validator.validate = mock_validate
        converter.to_saver_records = mock_to_records
        saver.save = mock_save

        await service.fetch_and_save()

        assert call_order == [
            "fetcher",
            "converter.from_dataframe",
            "validator",
            "converter.to_saver_records",
            "saver",
        ]

    @pytest.mark.asyncio
    async def test_result_has_elapsed_time(self):
        """elapsed_time が 0 以上であること."""
        service, fetcher, converter, validator, saver = _make_service()

        df = pd.DataFrame({"Open": [1.0]})
        fetcher.fetch = AsyncMock(return_value=df)
        converter.from_dataframe = MagicMock(return_value=_make_schema(1))
        validator.validate = MagicMock(return_value=_make_valid_result())
        converter.to_saver_records = MagicMock(return_value=[{}])
        saver.save = AsyncMock(return_value=1)

        result = await service.fetch_and_save()
        assert result.elapsed_time >= 0.0


class TestNikkei225ServiceFetchAndSaveEdgeCases:
    """境界値・空データのテスト."""

    @pytest.mark.asyncio
    async def test_empty_dataframe_returns_success_with_zero_counts(self):
        """空 DataFrame が返った場合、success=True で件数が 0 であること."""
        service, fetcher, converter, validator, saver = _make_service()

        fetcher.fetch = AsyncMock(return_value=pd.DataFrame())

        result = await service.fetch_and_save()

        assert result.success is True
        assert result.records_fetched == 0
        assert result.records_saved == 0
        assert result.warnings  # 警告が含まれること

    @pytest.mark.asyncio
    async def test_result_contains_required_attributes(self):
        """結果オブジェクトに success, records_fetched, records_saved, errors が含まれること."""
        service, fetcher, converter, validator, saver = _make_service()

        fetcher.fetch = AsyncMock(return_value=pd.DataFrame())

        result = await service.fetch_and_save()

        assert hasattr(result, "success")
        assert hasattr(result, "records_fetched")
        assert hasattr(result, "records_saved")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")


class TestNikkei225ServiceFetchAndSaveErrors:
    """エラーハンドリングのテスト."""

    @pytest.mark.asyncio
    async def test_fetcher_raises_yahoo_finance_error_returns_failure(self):
        """Fetcher が YahooFinanceError を投げた場合、success=False が返ること."""
        service, fetcher, converter, validator, saver = _make_service()

        fetcher.fetch = AsyncMock(side_effect=YahooFinanceError(message="API error"))

        result = await service.fetch_and_save()

        assert result.success is False
        assert result.records_fetched == 0
        assert result.records_saved == 0
        assert result.errors  # エラーが含まれること

    @pytest.mark.asyncio
    async def test_fetcher_raises_generic_exception_returns_failure(self):
        """Fetcher が一般例外を投げた場合も success=False が返ること."""
        service, fetcher, converter, validator, saver = _make_service()

        fetcher.fetch = AsyncMock(side_effect=RuntimeError("unexpected error"))

        result = await service.fetch_and_save()

        assert result.success is False
        assert result.errors

    @pytest.mark.asyncio
    async def test_saver_raises_exception_returns_failure(self):
        """Saver が例外を投げた場合、success=False が返ること."""
        service, fetcher, converter, validator, saver = _make_service()

        df = pd.DataFrame({"Open": [1.0]})
        fetcher.fetch = AsyncMock(return_value=df)
        converter.from_dataframe = MagicMock(return_value=_make_schema(1))
        validator.validate = MagicMock(return_value=_make_valid_result())
        converter.to_saver_records = MagicMock(return_value=[{}])
        saver.save = AsyncMock(side_effect=Exception("db error"))

        result = await service.fetch_and_save()

        assert result.success is False
        assert result.errors

    @pytest.mark.asyncio
    async def test_validation_failure_returns_failure_without_saving(self):
        """バリデーション失敗時、Saver が呼ばれずに success=False が返ること."""
        service, fetcher, converter, validator, saver = _make_service()

        df = pd.DataFrame({"Open": [1.0]})
        fetcher.fetch = AsyncMock(return_value=df)
        converter.from_dataframe = MagicMock(return_value=_make_schema(2))
        validator.validate = MagicMock(return_value=_make_invalid_result(["bad data"]))

        result = await service.fetch_and_save()

        assert result.success is False
        assert result.records_saved == 0
        # Saver は呼ばれていないこと
        saver.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_period_is_passed_to_fetcher(self):
        """max_period が Fetcher.fetch に渡されること."""
        service, fetcher, converter, validator, saver = _make_service()

        df = pd.DataFrame({"Open": [1.0]})
        fetcher.fetch = AsyncMock(return_value=df)
        converter.from_dataframe = MagicMock(return_value=_make_schema(1))
        validator.validate = MagicMock(return_value=_make_valid_result())
        converter.to_saver_records = MagicMock(return_value=[{}])
        saver.save = AsyncMock(return_value=1)

        await service.fetch_and_save(max_period=30)

        fetcher.fetch.assert_awaited_once_with(max_period=30)
