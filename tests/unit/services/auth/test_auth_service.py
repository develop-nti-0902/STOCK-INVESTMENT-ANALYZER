"""認証サービスのユニットテスト."""

import pytest

from app.services import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    hash_password,
    register_user,
    verify_password,
)


def test_hash_and_verify_password():
    """ハッシュ化と照合が正しく動作することを確認する."""
    # Arrange: 平文パスワードを用意
    pw = "strong-password-123"

    # Act: ハッシュ化
    hashed = hash_password(pw)

    # Assert: ハッシュと平文が一致すること
    assert verify_password(pw, hashed)


def test_jwt_create_and_decode(monkeypatch):
    """アクセストークンの作成と復号が整合することを確認する."""

    class MockSettings:
        SECRET_KEY = "test-secret"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 15

    # Arrange: 設定をモック
    monkeypatch.setattr("app.services.auth.auth_service.get_settings", lambda: MockSettings())

    # Act: トークン生成・復号
    token = create_access_token("user-id-1")
    payload = decode_access_token(token)

    # Assert: ペイロードに subject があること
    assert payload.get("sub") == "user-id-1"


@pytest.mark.asyncio
async def test_authenticate_and_register(monkeypatch):
    """認証と登録の基本フローが動作することを検証する (モック)."""

    class MockSettings:
        SECRET_KEY = "test-secret"
        ALGORITHM = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES = 15

    monkeypatch.setattr("app.services.auth.auth_service.get_settings", lambda: MockSettings())

    # Arrange: ダミーリポジトリとユーザを用意
    class DummyUser:
        def __init__(self, email, hashed):
            self.email = email
            self.hashed_password = hashed

    hashed = hash_password("pwd123")

    async def get_by_email(email):
        if email == "exists@example.com":
            return DummyUser(email, hashed)
        return None

    async def create_account(data):
        return DummyUser(data["email"], data["hashed_password"])

    repo = type("R", (), {})()
    repo.get_by_email = get_by_email
    repo.create_account = create_account

    # Act: 既存ユーザー認証と新規登録
    user = await authenticate_user(repo, "exists@example.com", "pwd123")
    new_user = await register_user(repo, "new@example.com", "newpwd", "New User")

    # Assert: 認証成功と登録結果の検証
    assert user is not None
    assert new_user.email == "new@example.com"
