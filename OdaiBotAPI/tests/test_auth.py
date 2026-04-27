"""認証 API (/auth/*) のテスト。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from OdaiBotAPI import deps
from OdaiBotAPI.deps import hash_password

from .conftest import ADMIN, BASE, GUILD_ID, make_cursor


# ─────────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────────
class TestLogin:
    _url = f"{BASE}/auth/login"

    def test_success(self, anon_client):
        password = "correct_pass"
        deps.db.query_one.return_value = {
            "id": 1, "username": "admin_user",
            "password_hash": hash_password(password),
            "role": "admin",
        }
        deps.db.execute.return_value = make_cursor()

        res = anon_client.post(self._url, json={"username": "admin_user", "password": password})

        assert res.status_code == 200
        body = res.json()
        assert body["token_type"] == "bearer"
        assert "access_token" in body
        assert body["role"] == "admin"

    def test_wrong_password_returns_401(self, anon_client):
        deps.db.query_one.return_value = {
            "id": 1, "username": "admin_user",
            "password_hash": hash_password("real_password"),
            "role": "admin",
        }

        res = anon_client.post(self._url, json={"username": "admin_user", "password": "wrong"})
        assert res.status_code == 401

    def test_user_not_found_returns_401(self, anon_client):
        deps.db.query_one.return_value = None

        res = anon_client.post(self._url, json={"username": "nobody", "password": "pass"})
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# POST /auth/register
# ─────────────────────────────────────────────────────────────
class TestRegister:
    _url = f"{BASE}/auth/register"

    def test_success(self, anon_client):
        invite = {
            "id": 10, "guild_id": GUILD_ID,
            "username": "new_user", "role": "user",
            "invite_token": "valid_token",
        }
        # 1回目: invite 取得 / 2回目: 重複チェック（None=重複なし）
        deps.db.query_one.side_effect = [invite, None]
        deps.db.execute.return_value = make_cursor()

        res = anon_client.post(self._url, json={
            "invite_token": "valid_token", "password": "password123"
        })

        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_short_password_returns_400(self, anon_client):
        res = anon_client.post(self._url, json={
            "invite_token": "any_token", "password": "short"
        })
        assert res.status_code == 400

    def test_invalid_token_returns_404(self, anon_client):
        deps.db.query_one.return_value = None  # invite not found

        res = anon_client.post(self._url, json={
            "invite_token": "bad_token", "password": "password123"
        })
        assert res.status_code == 404

    def test_duplicate_username_returns_409(self, anon_client):
        invite = {"id": 10, "guild_id": GUILD_ID, "username": "existing", "role": "user"}
        existing_user = {"id": 5}
        deps.db.query_one.side_effect = [invite, existing_user]

        res = anon_client.post(self._url, json={
            "invite_token": "valid_token", "password": "password123"
        })
        assert res.status_code == 409


# ─────────────────────────────────────────────────────────────
# POST /auth/invite
# ─────────────────────────────────────────────────────────────
class TestCreateInvite:
    _url = f"{BASE}/auth/invite"

    def test_success(self, admin_client):
        deps.db.query_one.return_value = None  # no duplicate
        deps.db.execute.return_value = make_cursor()

        res = admin_client.post(self._url, json={"username": "new_user", "role": "user"})

        assert res.status_code == 200
        body = res.json()
        assert "invite_token" in body
        assert "expires_at" in body

    def test_invalid_role_returns_400(self, admin_client):
        res = admin_client.post(self._url, json={"username": "u", "role": "superadmin"})
        assert res.status_code == 400

    def test_duplicate_username_returns_409(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}  # already exists

        res = admin_client.post(self._url, json={"username": "existing", "role": "user"})
        assert res.status_code == 409


# ─────────────────────────────────────────────────────────────
# GET /auth/users
# ─────────────────────────────────────────────────────────────
class TestListUsers:
    _url = f"{BASE}/auth/users"

    def test_success(self, admin_client):
        from datetime import datetime
        now = datetime.utcnow()
        deps.db.query.return_value = [
            {"id": 1, "username": "admin_user", "role": "admin", "created_at": now, "updated_at": now},
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert len(res.json()) == 1


# ─────────────────────────────────────────────────────────────
# POST /auth/users
# ─────────────────────────────────────────────────────────────
class TestCreateUser:
    """create_user はルート内で has_guild_users / get_optional_current_user を直接呼ぶため、
    ギルドにユーザーがいない（初回作成）シナリオでテストする。"""
    _url = f"{BASE}/auth/users"

    def test_success_first_user(self, anon_client):
        """ギルドにユーザーが存在しない場合は認証なしで作成できる。"""
        from datetime import datetime
        now = datetime.utcnow()
        deps.db.query_one.side_effect = [
            None,   # has_guild_users → False（ユーザーなし）
            None,   # duplicate check → None
            {"id": 99, "username": "first_user", "role": "admin", "created_at": now, "updated_at": now},
        ]
        deps.db.execute.return_value = make_cursor(99)

        res = anon_client.post(self._url, json={
            "username": "first_user", "password": "password123", "role": "admin"
        })
        assert res.status_code == 200
        assert res.json()["username"] == "first_user"

    def test_short_password_returns_400(self, anon_client):
        deps.db.query_one.return_value = None  # has_guild_users → False
        res = anon_client.post(self._url, json={
            "username": "u", "password": "short", "role": "user"
        })
        assert res.status_code == 400

    def test_duplicate_username_returns_409(self, anon_client):
        deps.db.query_one.side_effect = [
            None,      # has_guild_users → False
            {"id": 5}, # duplicate check → exists
        ]
        res = anon_client.post(self._url, json={
            "username": "existing", "password": "password123", "role": "user"
        })
        assert res.status_code == 409


# ─────────────────────────────────────────────────────────────
# PUT /auth/users/{user_id}
# ─────────────────────────────────────────────────────────────
class TestUpdateUser:
    def test_success(self, admin_client):
        from datetime import datetime
        now = datetime.utcnow()
        deps.db.query_one.side_effect = [
            {"id": 99},  # user exists
            {"id": 99, "username": "u", "role": "user", "created_at": now, "updated_at": now},
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(f"{BASE}/auth/users/99", json={"role": "admin"})
        assert res.status_code == 200

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.put(f"{BASE}/auth/users/999", json={"role": "user"})
        assert res.status_code == 404

    def test_no_update_fields_returns_400(self, admin_client):
        deps.db.query_one.return_value = {"id": 99}

        res = admin_client.put(f"{BASE}/auth/users/99", json={})
        assert res.status_code == 400


# ─────────────────────────────────────────────────────────────
# DELETE /auth/users/{user_id}
# ─────────────────────────────────────────────────────────────
class TestDeleteUser:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 99}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{BASE}/auth/users/99")
        assert res.status_code == 204

    def test_self_delete_returns_400(self, admin_client):
        # ADMIN["id"] == 1 なので user_id=1 は自己削除
        res = admin_client.delete(f"{BASE}/auth/users/1")
        assert res.status_code == 400

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{BASE}/auth/users/999")
        assert res.status_code == 404
