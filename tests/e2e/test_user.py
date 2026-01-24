import asyncio
import uuid

from tests.e2e.utils import write_csv_artifact


def test_get_me_and_change_password(client):
    """GET /api/v1/accounts/me と PUT /api/v1/accounts/me/password のE2Eテスト

    フロー:
      1. ユーザー登録
      2. ログインしてトークン取得
      3. `/accounts/me` でプロフィール取得を確認
      4. `/accounts/me/password` でパスワード変更（204）を実行
      5. 古いパスワードでのログインが401になることを確認
      6. 新しいパスワードでのログインが成功することを確認
      7. クリーンアップでユーザーを削除
    """
    email = f"test-{uuid.uuid4().hex}@example.com"
    old_password = "OldP@ssw0rd"
    new_password = "NewP@ssw0rd"

    register_payload = {
        "email": email,
        "password": old_password,
        "display_name": "E2E Me Tester",
    }

    try:
        # 登録
        r = client.post("/api/v1/auth/register", json=register_payload)
        assert r.status_code == 201

        # artifact: user registered (CSV, 固定名規約: file_func_table_flow)
        try:
            base_name = "test_user_test_get_me_and_change_password_accounts_1"
            write_csv_artifact(
                {
                    "event": "user_registered",
                    "email": email,
                    "status_code": r.status_code,
                },
                name=base_name,
            )
        except Exception:
            pass

        # ログインしてトークン取得
        login_payload = {"email": email, "password": old_password}
        resp = client.post("/api/v1/auth/login", json=login_payload)
        assert resp.status_code == 200
        token = resp.json().get("access_token")
        assert token

        headers = {"Authorization": f"Bearer {token}"}

        # /accounts/me を取得
        me_resp = client.get("/api/v1/accounts/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data.get("email") == email

        # パスワード変更
        change_payload = {
            "current_password": old_password,
            "new_password": new_password,
        }
        change_resp = client.put(
            "/api/v1/accounts/me/password",
            json=change_payload,
            headers=headers,
        )
        assert change_resp.status_code == 204

        # artifact: password changed (CSV, 固定名規約: file_func_table_flow)
        try:
            base_name = "test_user_test_get_me_and_change_password_accounts_4"
            write_csv_artifact(
                {
                    "event": "password_changed",
                    "email": email,
                    "status_code": change_resp.status_code,
                },
                name=base_name,
            )
        except Exception:
            pass

        # 古いパスワードでログイン失敗
        old_login = client.post("/api/v1/auth/login", json=login_payload)
        assert old_login.status_code == 401

        # 新しいパスワードでログイン成功
        new_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_password},
        )
        assert new_login.status_code == 200
        assert new_login.json().get("access_token")

        # ここで API によるユーザー無効化 (DELETE /api/v1/accounts/me)
        new_token = new_login.json().get("access_token")
        del_headers = {"Authorization": f"Bearer {new_token}"}
        del_resp = client.delete("/api/v1/accounts/me", headers=del_headers)
        assert del_resp.status_code == 204

        # 無効化後、同じトークンで /accounts/me にアクセスすると 403 になる
        me_after = client.get("/api/v1/accounts/me", headers=del_headers)
        assert me_after.status_code == 403

    finally:
        # クリーンアップ
        from sqlalchemy import text

        from app.utils.database import get_engine

        async def _cleanup(target_email: str) -> None:
            engine = get_engine()
            async with engine.connect() as conn:
                async with conn.begin():
                    await conn.execute(
                        text("DELETE FROM accounts WHERE email = :email"),
                        {"email": target_email},
                    )

        try:
            asyncio.run(_cleanup(email))
        except Exception:
            pass
