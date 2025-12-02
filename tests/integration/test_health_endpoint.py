def test_health_endpoint_via_client(client):
    """`/health` エンドポイントに対して統合的にリクエストを投げて検証します。

    - FastAPI の `TestClient` を使用して実際のルーティングを経由します。
    - レスポンスの HTTP ステータスと JSON ボディを検証します。
    """
    # Arrange: 特段のセットアップは不要（client fixture を利用）

    # Act: /health エンドポイントへ GET リクエストを送信
    response = client.get("/health")

    # Assert: ステータスコードと JSON ボディを検証
    assert response.status_code == 200
    json_body = response.json()
    assert isinstance(json_body, dict)
    assert json_body.get("status") == "ok"
