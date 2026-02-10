"""`StockMasterFetcher` の単体テスト.

このファイルは大幅にリファクタされた `fetcher` を前提に、
初期化と内部ユーティリティ（正規化関数）、および `fetch_all` の
主要な分岐（ダウンロード例外の変換、正常系のフロー呼び出し）を検証します。
"""

import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
import pandas as pd
import pytest

from app.exceptions.business import ServiceError
from app.exceptions.external_api import JPXAPIError
from app.exceptions.validation import FieldValidationError

# StockMasterRaw is not needed in these tests
from app.services.market_data.stock_master.fetcher import StockMasterFetcher


def test_initialization_default_and_custom_url():
    """デフォルト URL とカスタム URL の初期化を検証する."""
    f = StockMasterFetcher()
    assert f.url == StockMasterFetcher.DEFAULT_URL

    custom = "https://example.test/jpx.xls"
    f2 = StockMasterFetcher(url=custom)
    assert f2.url == custom


def test_normalize_stock_code_valid_and_invalid():
    """`_normalize_stock_code` の正常系・異常系を検証する."""
    f = StockMasterFetcher()

    assert f._normalize_stock_code("1301") == "1301"
    assert f._normalize_stock_code(1301) == "1301"

    with pytest.raises(FieldValidationError):
        f._normalize_stock_code(None)


def test_normalize_stock_name_valid_and_invalid():
    """`_normalize_stock_name` の正常系・異常系を検証する."""
    f = StockMasterFetcher()

    assert f._normalize_stock_name(" 極洋 ") == "極洋"

    with pytest.raises(FieldValidationError):
        f._normalize_stock_name("")


def test_normalize_date_various_formats():
    """`_normalize_date` が複数形式を YYYYMMDD に正規化することを検証する."""
    f = StockMasterFetcher()

    assert f._normalize_date("2025/12/07") == "20251207"
    assert f._normalize_date("2025-12-07") == "20251207"
    assert f._normalize_date("20251207") == "20251207"
    assert f._normalize_date("2025/1/7") == "20250107"
    assert f._normalize_date(None) is None


def test_fetch_all_raises_jpx_api_error_on_download_exception():
    """ダウンロードで aiohttp.ClientError が発生した場合 JPXAPIError に変換されることを検証する."""
    f = StockMasterFetcher()

    async def raise_client_error():
        raise aiohttp.ClientError("network")

    with patch.object(f, "_download_excel", new_callable=AsyncMock) as md:
        md.side_effect = raise_client_error

        with pytest.raises(JPXAPIError):
            asyncio.run(f.fetch_all())


def test_fetch_all_calls_parse_and_normalize():
    """正常系では _parse_excel と _normalize_data が呼ばれ、その結果が返ることを検証する."""
    f = StockMasterFetcher()

    excel_bytes = b"dummy"
    parsed_df = object()
    normalized = ["rec1", "rec2"]

    with patch.object(f, "_download_excel", new_callable=AsyncMock) as md:
        with patch.object(f, "_parse_excel", new_callable=AsyncMock) as mp:
            with patch.object(f, "_normalize_data", new_callable=AsyncMock) as mn:
                md.return_value = excel_bytes
                mp.return_value = parsed_df
                mn.return_value = normalized

                result = asyncio.run(f.fetch_all())

    assert result == normalized
    mp.assert_called_once_with(excel_bytes)
    mn.assert_called_once_with(parsed_df)


def test_fetch_all_raises_jpx_api_error_on_parse_service_error():
    """_parse_excel が ServiceError を出す場合 JPXAPIError に変換されることを検証する."""
    f = StockMasterFetcher()

    async def parsed_raise(*_args, **_kwargs):
        raise ServiceError(message="parse fail")

    with patch.object(f, "_download_excel", new_callable=AsyncMock) as md:
        with patch.object(f, "_parse_excel", new_callable=AsyncMock) as mp:
            md.return_value = b"dummy"
            mp.side_effect = parsed_raise

            with pytest.raises(JPXAPIError):
                asyncio.run(f.fetch_all())


def test_parse_excel_raises_service_error_on_bad_excel():
    """内部で pandas.read_excel が失敗すると ServiceError が発生することを検証する."""
    f = StockMasterFetcher()

    # pandas の read_excel を例外にする
    with patch("app.services.market_data.stock_master.fetcher.pd.read_excel") as pr:
        pr.side_effect = ValueError("bad excel")

        with pytest.raises(ServiceError):
            asyncio.run(f._parse_excel(b"notxls"))


def test_normalize_data_partial_and_all_invalid():
    """正常行とエラー行が混在する場合と全行エラーで ServiceError を確認."""
    f = StockMasterFetcher()

    valid_row = {
        "コード": "1301",
        "銘柄名": " 極洋 ",
        "市場・商品区分": "TSE",
        "日付": "2025/12/07",
    }
    invalid_row = {"コード": None, "銘柄名": None, "市場・商品区分": None, "日付": None}

    df = pd.DataFrame([valid_row, invalid_row])

    # 部分的に正常・異常が混在している場合は正常レコードのみ返る
    result = asyncio.run(f._normalize_data(df))
    assert isinstance(result, list)
    assert len(result) == 1

    # 全行が無効な場合は ServiceError を送出する
    df_all_invalid = pd.DataFrame([invalid_row])
    with pytest.raises(ServiceError):
        asyncio.run(f._normalize_data(df_all_invalid))


def test_normalize_data_handles_validation_error_rows():
    """StockMasterRaw.model_validate が ValidationError を投げるケースを検証する."""
    f = StockMasterFetcher()

    row = {"コード": "1301", "銘柄名": "極洋"}
    df = pd.DataFrame([row])

    # fetcher モジュール内で参照されている ValidationError を一時的に置き換え、
    # model_validate がその例外を投げるケースを検証する
    FakeVal = type("FakeVal", (Exception,), {})

    with patch("app.services.market_data.stock_master.fetcher.ValidationError", new=FakeVal):
        with patch(
            "app.services.market_data.stock_master.fetcher.StockMasterRaw.model_validate"
        ) as mv:
            mv.side_effect = FakeVal("validation failed")

            with pytest.raises(ServiceError):
                asyncio.run(f._normalize_data(df))


def test_fetch_and_fetch_batch_not_implemented():
    """fetch / fetch_batch が NotImplementedError を投げることを検証する."""
    f = StockMasterFetcher()

    with pytest.raises(NotImplementedError):
        asyncio.run(f.fetch("1301"))

    with pytest.raises(NotImplementedError):
        asyncio.run(f.fetch_batch(["1301", "7203"]))
