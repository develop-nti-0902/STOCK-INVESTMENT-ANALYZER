"""refresh APIエンドポイントの統合テスト."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_latest_stock_success(
    client: AsyncClient, db_session: AsyncSession
):
    """正常系: 指定したシンボルの最新株価情報を取得できる."""
    symbol = "TEST1.T"

    # テストデータを挿入
    await db_session.execute(
        text(
            """
            INSERT INTO stocks_1d (
                symbol, timestamp, open, high, low, close, adj_close, volume,
                created_at, updated_at
            )
            VALUES (
                :symbol,
                '2026-01-22 00:00:00+00:00',
                1000.0000,
                1100.0000,
                950.0000,
                1050.0000,
                1050.0000,
                1000000,
                NOW(),
                NOW()
            )
            """
        ),
        {"symbol": symbol},
    )
    await db_session.commit()

    # マテリアライズドビューを手動でリフレッシュ
    await db_session.execute(
        text("REFRESH MATERIALIZED VIEW latest_stocks_1d")
    )
    await db_session.commit()

    # APIを呼び出し
    response = await client.get(f"/api/v1/views/latest-stocks/{symbol}")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert Decimal(str(data["close"])) == Decimal("1050.0000")
    assert data["volume"] == 1000000


@pytest.mark.asyncio
async def test_get_latest_stock_not_found(client: AsyncClient):
    """異常系: 存在しないシンボルを指定した場合に404エラーが返る."""
    symbol = "NOTFOUND"

    response = await client.get(f"/api/v1/views/latest-stocks/{symbol}")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()
