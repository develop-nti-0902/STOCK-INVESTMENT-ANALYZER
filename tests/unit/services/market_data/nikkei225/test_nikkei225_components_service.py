"""Nikkei225ComponentsServiceのユニットテスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market_data.nikkei225 import Nikkei225Component
from app.services.market_data.nikkei225.nikkei225_components_service import (
    Nikkei225ComponentsService,
)

# サンプルCSVデータ（日経225公式フォーマット）
SAMPLE_CSV_225_ROWS = """\
対象日付,コード,銘柄名,株価換算係数,業種,セクター
2026/04/18,7203,トヨタ自動車,50,輸送用機器,自動車
2026/04/18,9984,ソフトバンクグループ,10,情報・通信業,IT
2026/04/18,6758,ソニーグループ,10,電気機器,電気・精密
""".strip()

SAMPLE_CSV_INVALID_ROW = """\
対象日付,コード,銘柄名,株価換算係数,業種,セクター
2026/04/18,7203,トヨタ自動車,50,輸送用機器,自動車
2026/04/18,INVALID,不正コード,abc,情報・通信業,IT
2026/04/18,6758,ソニーグループ,10,電気機器,電気・精密
""".strip()


@pytest.fixture
def mock_session():
    """モックDBセッション."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    """Nikkei225ComponentsServiceインスタンス."""
    return Nikkei225ComponentsService(session=mock_session)


def _make_mock_component(stock_code: str) -> Nikkei225Component:
    """テスト用の Nikkei225Component モックを生成する."""
    comp = MagicMock(spec=Nikkei225Component)
    comp.stock_code = stock_code
    return comp


class TestFetchAndUpdate:
    """fetch_and_update のテスト."""

    def _make_mock_http_session(self, csv_bytes: bytes) -> MagicMock:
        """aiohttp.ClientSession のモックを生成する."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.read = AsyncMock(return_value=csv_bytes)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_http_session = MagicMock()
        mock_http_session.get = MagicMock(return_value=mock_response)
        mock_http_session.__aenter__ = AsyncMock(return_value=mock_http_session)
        mock_http_session.__aexit__ = AsyncMock(return_value=None)
        return mock_http_session

    @pytest.mark.asyncio
    async def test_fetch_and_update_success(self, service):
        """正常なCSVを渡した場合、レコードが保存されること."""
        csv_bytes = SAMPLE_CSV_225_ROWS.encode("shift_jis")
        mock_http_session = self._make_mock_http_session(csv_bytes)

        saved = [_make_mock_component(c) for c in ["7203", "9984", "6758"]]
        service.repository.upsert_batch = AsyncMock(return_value=saved)

        with patch("aiohttp.ClientSession", return_value=mock_http_session):
            result = await service.fetch_and_update()

        assert result["success"] is True
        assert result["count"] == 3
        assert result["error"] is None
        service.repository.upsert_batch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fetch_and_update_network_error(self, service):
        """aiohttp.ClientError 発生時、success=False が返ること."""
        mock_http_session = MagicMock()
        mock_http_session.get = MagicMock(side_effect=aiohttp.ClientError("timeout"))
        mock_http_session.__aenter__ = AsyncMock(return_value=mock_http_session)
        mock_http_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_http_session):
            result = await service.fetch_and_update()

        assert result["success"] is False
        assert result["count"] == 0
        assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_fetch_and_update_parse_error(self, service):
        """不正な行があっても正常な行は保存されること."""
        csv_bytes = SAMPLE_CSV_INVALID_ROW.encode("shift_jis")
        mock_http_session = self._make_mock_http_session(csv_bytes)

        saved = [_make_mock_component("7203"), _make_mock_component("6758")]
        service.repository.upsert_batch = AsyncMock(return_value=saved)

        with patch("aiohttp.ClientSession", return_value=mock_http_session):
            result = await service.fetch_and_update()

        # 不正行はスキップされ、残り2件が保存される
        assert result["success"] is True
        assert result["count"] == 2
        assert result["error"] is None

        # upsert_batch に渡されたリストには不正行が含まれないこと
        call_args = service.repository.upsert_batch.call_args[0][0]
        codes = [r["stock_code"] for r in call_args]
        assert "INVALID" not in codes
        assert "7203" in codes
        assert "6758" in codes


class TestIsInNikkei225:
    """is_in_nikkei225 のテスト."""

    @pytest.mark.asyncio
    async def test_is_in_nikkei225_true(self, service):
        """`find_by_code` がレコードを返す場合、True になること."""
        service.repository.find_by_code = AsyncMock(return_value=_make_mock_component("7203"))

        result = await service.is_in_nikkei225("7203")

        assert result is True
        service.repository.find_by_code.assert_awaited_once_with("7203")

    @pytest.mark.asyncio
    async def test_is_in_nikkei225_false(self, service):
        """`find_by_code` が None を返す場合、False になること."""
        service.repository.find_by_code = AsyncMock(return_value=None)

        result = await service.is_in_nikkei225("9999")

        assert result is False
        service.repository.find_by_code.assert_awaited_once_with("9999")
