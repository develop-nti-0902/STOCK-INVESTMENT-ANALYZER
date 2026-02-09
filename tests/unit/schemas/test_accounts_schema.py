"""Account schema のバリデーション単体テスト."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    AccountLoginRequest,
    AccountRegisterRequest,
    PasswordChangeRequest,
    TokenResponse,
)


def test_account_register_valid():
    """有効な登録リクエストが受け付けられることを確認する."""
    req = AccountRegisterRequest(
        email="user@example.com", password="Passw0rd1", display_name="User"
    )
    assert req.email == "user@example.com"


@pytest.mark.parametrize(
    "email",
    ["not-an-email", "", "user@", "user@domain"],
)
def test_account_register_invalid_email(email):
    """不正なメールアドレスでバリデーションエラーが発生することを確認する."""
    with pytest.raises(ValidationError):
        AccountRegisterRequest(email=email, password="Passw0rd1", display_name="User")


def test_account_register_short_password():
    """パスワードが短い場合に ValidationError が発生する."""
    with pytest.raises(ValidationError):
        AccountRegisterRequest(email="a@b.com", password="abc", display_name="User")


def test_account_register_numeric_only_password():
    """数字のみのパスワードが許容されることを確認する."""
    req = AccountRegisterRequest(email="n@d.com", password="12345", display_name="Num")
    assert req.password == "12345"


def test_account_register_alpha_only_password():
    """英字のみのパスワードが許容されることを確認する."""
    req = AccountRegisterRequest(email="a@b.com", password="abcdef", display_name="Alpha")
    assert req.password == "abcdef"


def test_account_login_valid():
    """ログインリクエストの基本形がパースされることを確認する."""
    req = AccountLoginRequest(email="u@example.com", password="secret")
    assert req.email == "u@example.com"


def test_password_change_validator():
    """パスワード変更の検証で短い新パスワードが拒否されることを確認する."""
    with pytest.raises(ValidationError):
        PasswordChangeRequest(current_password="old", new_password="a")


def test_token_response_shape():
    """トークンレスポンスのフィールド形状を検証する."""
    tr = TokenResponse(access_token="tok", token_type="bearer")
    assert tr.access_token == "tok"
