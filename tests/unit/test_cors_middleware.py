"""CORS ミドルウェアの挙動に関する単体テスト."""

from fastapi.testclient import TestClient

from app.main import app
from app.utils.config import get_settings


def test_cors_allows_development_origin():
    """プリフライトリクエストで設定された開発オリジンが許可されることを確認する."""
    settings = get_settings()
    client = TestClient(app)

    origin = (
        settings.CORS_ALLOW_ORIGINS[0] if settings.CORS_ALLOW_ORIGINS else "http://localhost:3000"
    )
    headers = {"Origin": origin, "Access-Control-Request-Method": "GET"}

    resp = client.options("/health", headers=headers)
    assert resp.status_code in (200, 204)

    # レスポンスヘッダで Access-Control-Allow-Origin が期待通り返る
    assert resp.headers.get("access-control-allow-origin") == origin

    if settings.CORS_ALLOW_CREDENTIALS:
        assert resp.headers.get("access-control-allow-credentials") == "true"
