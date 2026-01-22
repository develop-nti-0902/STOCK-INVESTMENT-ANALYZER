"""latest_stocks APIエンドポイントの統合テスト (E2E用ファイル名)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.api.dependencies.services import get_latest_stocks_service
from app.exceptions.business import ServiceError


class _FakeLatestStocksService:
    def __init__(
        self, payload: dict | None = None, exc: Exception | None = None
    ):
        self._payload = payload
        self._exc = exc

    async def get_latest_stock(self, symbol: str):
        if self._exc:
            raise self._exc
        return self._payload


@pytest.mark.asyncio
async def test_get_latest_stock_success(client):
    """正常系: 指定したシンボルの最新株価情報を取得できる."""
    symbol = "TEST1.T"

    # モックサービスでエンドポイントの依存性を上書きしてDBに触らず検証
    payload = {
        "id": 1,
        "symbol": symbol,
        "timestamp": "2026-01-22T00:00:00+00:00",
        "open": "1000.0000",
        "high": "1100.0000",
        "low": "950.0000",
        "close": "1050.0000",
        "adj_close": "1050.0000",
        "volume": 1000000,
    }

    fake_service = _FakeLatestStocksService(payload=payload)
    # TestClient のアプリに対して依存性をオーバーライド
    client.app.dependency_overrides[get_latest_stocks_service] = (
        lambda: fake_service
    )

    # APIを呼び出し（TestClient を使うので同期的に呼ぶ）
    response = client.get(f"/api/v1/views/latest-stocks/{symbol}")

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == symbol
    assert Decimal(str(data["close"])) == Decimal("1050.0000")
    assert data["volume"] == 1000000


@pytest.mark.asyncio
async def test_get_latest_stock_not_found(client):
    """異常系: 存在しないシンボルを指定した場合に404エラーが返る."""
    symbol = "NOTFOUND"

    # オーバーライドして ServiceError を発生させるモックを返す
    fake_service = _FakeLatestStocksService(
        exc=ServiceError(message=f"Symbol {symbol} not found")
    )
    client.app.dependency_overrides[get_latest_stocks_service] = (
        lambda: fake_service
    )

    response = client.get(f"/api/v1/views/latest-stocks/{symbol}")

    assert response.status_code == 404
    data = response.json()
    # エラーハンドラは統一フォーマットを返すため、ネストされた error.message を確認する
    assert "not found" in data["error"]["message"].lower()
