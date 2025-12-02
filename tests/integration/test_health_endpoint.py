import pytest

from app.main import health


@pytest.mark.asyncio
async def test_health_endpoint():
    """ヘルスチェックのエンドポイント関数を直接呼び出して応答を検証します。"""
    result = await health()
    assert isinstance(result, dict)
    assert result.get("status") == "ok"
