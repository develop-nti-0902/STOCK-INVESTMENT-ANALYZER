from app.main import app as fastapi_app


def test_app_startup_has_settings(client):
    """アプリケーション起動時に設定が `app.state.settings` に設定されていることを検証します。

    - `TestClient` を経由してアプリを起動（コンテキスト内）し、`app.state` に `settings` が存在するか確認します。
    - 設定オブジェクトが少なくとも主要な属性を持っていることを確認します（存在確認のみ）。
    """
    # Arrange: client fixture を通してアプリが起動するテストコンテキストを準備

    # Act: ヘルスチェックを叩いて起動経路を通す
    response = client.get("/health")

    # Assert: /health の成功と app.state.settings の存在を検証
    assert response.status_code == 200
    assert hasattr(
        fastapi_app.state, "settings"
    ), "app.state.settings が存在しません"

    settings = fastapi_app.state.settings
    # 最低限の属性が存在することを確認（値まではテストしない）
    for attr in ("APP_NAME", "APP_VERSION", "ENV"):
        assert hasattr(settings, attr), f"settings に {attr} が存在しません"
