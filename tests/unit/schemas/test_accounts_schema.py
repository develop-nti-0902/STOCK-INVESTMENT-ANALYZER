import pytest
from pydantic import ValidationError

from app.schemas import (
    AccountLoginRequest,
    AccountRegisterRequest,
    PasswordChangeRequest,
    TokenResponse,
)


def test_account_register_valid():
    req = AccountRegisterRequest(
        email="user@example.com", password="Passw0rd1", display_name="User"
    )
    assert req.email == "user@example.com"


@pytest.mark.parametrize(
    "email",
    ["not-an-email", "", "user@", "user@domain"],
)
def test_account_register_invalid_email(email):
    with pytest.raises(ValidationError):
        AccountRegisterRequest(
            email=email, password="Passw0rd1", display_name="User"
        )


def test_account_register_short_password():
    # 新要件: パスワードは4文字以上必要 => 3文字はエラー
    with pytest.raises(ValidationError):
        AccountRegisterRequest(
            email="a@b.com", password="abc", display_name="User"
        )


def test_account_register_numeric_only_password():
    # 数字のみパスワードは許容される
    req = AccountRegisterRequest(
        email="n@d.com", password="12345", display_name="Num"
    )
    assert req.password == "12345"


def test_account_register_alpha_only_password():
    # 文字のみパスワードは許容される
    req = AccountRegisterRequest(
        email="a@b.com", password="abcdef", display_name="Alpha"
    )
    assert req.password == "abcdef"


def test_account_login_valid():
    req = AccountLoginRequest(email="u@example.com", password="secret")
    assert req.email == "u@example.com"


def test_password_change_validator():
    # 新要件: new_passwordは4文字以上が必要
    with pytest.raises(ValidationError):
        PasswordChangeRequest(current_password="old", new_password="a")


def test_token_response_shape():
    tr = TokenResponse(access_token="tok", token_type="bearer")
    assert tr.access_token == "tok"
