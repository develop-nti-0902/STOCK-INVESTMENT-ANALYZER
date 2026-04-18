"""Nikkei225Matcherのユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.nikkei225_matcher import Nikkei225Matcher


@pytest.fixture
def mock_session():
    """モックDBセッション."""
    return AsyncMock(spec=AsyncSession)


def test_yahoo_ticker_to_code_basic():
    """`7203.T` → `7203` に変換されること."""
    result = Nikkei225Matcher.yahoo_ticker_to_code("7203.T")
    assert result == "7203"


def test_yahoo_ticker_to_code_no_suffix():
    """ドットなし `7203` → `7203` のままであること."""
    result = Nikkei225Matcher.yahoo_ticker_to_code("7203")
    assert result == "7203"


def test_yahoo_ticker_to_code_4digit():
    """`1332.T` → `1332` に変換されること."""
    result = Nikkei225Matcher.yahoo_ticker_to_code("1332.T")
    assert result == "1332"


@pytest.mark.asyncio
async def test_is_nikkei225_true(mock_session):
    """`is_in_nikkei225` が True を返す場合、`is_nikkei225` も True になること."""
    matcher = Nikkei225Matcher(mock_session)
    matcher.service.is_in_nikkei225 = AsyncMock(return_value=True)

    result = await matcher.is_nikkei225("7203.T")

    assert result is True
    matcher.service.is_in_nikkei225.assert_awaited_once_with("7203")


@pytest.mark.asyncio
async def test_is_nikkei225_false(mock_session):
    """`is_in_nikkei225` が False を返す場合、`is_nikkei225` も False になること."""
    matcher = Nikkei225Matcher(mock_session)
    matcher.service.is_in_nikkei225 = AsyncMock(return_value=False)

    result = await matcher.is_nikkei225("9999.T")

    assert result is False
    matcher.service.is_in_nikkei225.assert_awaited_once_with("9999")
