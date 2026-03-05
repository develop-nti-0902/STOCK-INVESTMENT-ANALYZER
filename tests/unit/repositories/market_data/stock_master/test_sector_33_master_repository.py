"""Tests for Sector33MasterRepository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.market_data.stock_master import Sector33Master
from app.repositories.market_data.stock_master import Sector33MasterRepository
from app.services.screening.models import ScreeningConfig


@pytest.mark.asyncio
async def test_sector_33_master_repository_get_by_code():
    """Sector33MasterRepository.get_by_code() のテスト."""
    mock_session = AsyncMock()
    sector = Sector33Master(id=1, code="08", name="水産・農林業")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=sector)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = Sector33MasterRepository(session=mock_session)
    result = await repo.get_by_code("08")

    assert result == sector
    assert result.code == "08"


@pytest.mark.asyncio
async def test_as_config_dict():
    """Sector33MasterRepository.as_config_dict() のテスト."""
    mock_session = AsyncMock()

    # テストデータを作成（3件）
    records = [
        Sector33Master(id=1, code="08", name="医薬品"),
        Sector33Master(id=2, code="16", name="電気機器"),
        Sector33Master(id=3, code="33", name="サービス業"),
    ]

    # list_all メソッドをモックする
    # scalars().all() の戻り値をカスタマイズ
    mock_scalars = MagicMock()
    mock_scalars.all = MagicMock(return_value=records)
    mock_result = MagicMock()
    mock_result.scalars = MagicMock(return_value=mock_scalars)
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = Sector33MasterRepository(session=mock_session)
    result = await repo.as_config_dict()

    # 戻り値が Dict か確認
    assert isinstance(result, dict)

    # キーが業種コード（"08", "16", "33"）であることを確認
    assert set(result.keys()) == {"08", "16", "33"}

    # 値が ScreeningConfig インスタンスか確認
    for config in result.values():
        assert isinstance(config, ScreeningConfig)

    # industry_code と industry_name が正しくマッピングされていることを確認
    assert result["08"].industry_code == "08"
    assert result["08"].industry_name == "医薬品"
    assert result["16"].industry_code == "16"
    assert result["16"].industry_name == "電気機器"
    assert result["33"].industry_code == "33"
    assert result["33"].industry_name == "サービス業"
