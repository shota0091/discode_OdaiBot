"""認証 API の追加エンドポイントテスト。

パスワードリセット・BAN管理・招待管理・ロック解除・ユーザー操作・プロフィールを検証する。
"""
from __future__ import annotations

from datetime import datetime

import pytest

from OdaiBotAPI import deps
from OdaiBotAPI.deps import hash_password

from .conftest import ADMIN, USER, BASE, GUILD_ID, make_cursor

_NOW = datetime.utcnow()

_USER_ROW = {
    "id": 2, "username": "test_user", "display_name": None,
    "role": "user", "login_attempts": 0, "locked_until": None,
    "login_locked": 0, "is_banned": 0,
    "created_at": _NOW, "updated_at": _NOW,
}


# ─────────────────────────────────────────────────────────────
# POST /auth/reset-password
# ─────────────────────────────────────────────────────────────
class TestResetPassword:
    _url = f"{BASE}/auth/reset-password"

    def test_success(self, anon_client):
        invite = {"id": 10, "guild_id": GUILD_ID, "username": "test_user"}
        user = {"id": 2}
        deps.db.query_one.side_effect = [invite, user]
        deps.db.execute.return_value = make_cursor()

        res = anon_client.post(self._url, json={
            "invite_token": "valid_token", "password": "newpassword123"
        })
        assert res.status_code == 200
        assert "message" in res.json()

    def test_invalid_token_returns_404(self, anon_client):
        deps.db.query_one.return_value = None  # invite not found

        res = anon_client.post(self._url, json={
            "invite_token": "bad_token", "password": "newpassword123"
        })
        assert res.status_code == 404

    def test_user_not_found_returns_404(self, anon_client):
        invite = {"id": 10, "guild_id": GUILD_ID, "username": "ghost"}
        deps.db.query_one.side_effect = [invite, None]

        res = anon_client.post(self._url, json={
            "invite_token": "valid_token", "password": "newpassword123"
        })
        assert res.status_code == 404

    def test_short_password_returns_400(self, anon_client):
        invite = {"id": 10, "guild_id": GUILD_ID, "username": "test_user"}
        deps.db.query_one.return_value = invite

        res = anon_client.post(self._url, json={
            "invite_token": "valid_token", "password": "short"
        })
        assert res.status_code == 400


# ─────────────────────────────────────────────────────────────
# GET /auth/invite-info
# ─────────────────────────────────────────────────────────────
class TestGetInviteInfo:
    def test_success(self, anon_client):
        deps.db.query_one.return_value = {"username": "new_user"}

        res = anon_client.get(f"{BASE}/auth/invite-info", params={"token": "valid_token"})
        assert res.status_code == 200
        assert res.json()["username"] == "new_user"

    def test_invalid_token_returns_404(self, anon_client):
        deps.db.query_one.return_value = None

        res = anon_client.get(f"{BASE}/auth/invite-info", params={"token": "bad_token"})
        assert res.status_code == 404


# ─────────────────────────────────────────────────────────────
# GET/DELETE /auth/bans
# ─────────────────────────────────────────────────────────────
class TestListBans:
    _url = f"{BASE}/auth/bans"

    def test_success(self, admin_client):
        deps.db.query.return_value = [{"id": 1, "username": "bad_user", "banned_at": _NOW}]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["username"] == "bad_user"

    def test_empty_list(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401

    def test_non_admin_returns_403(self, user_client):
        res = user_client.get(self._url)
        assert res.status_code == 403


class TestRemoveBan:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{BASE}/auth/bans/1")
        assert res.status_code == 204

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{BASE}/auth/bans/999")
        assert res.status_code == 404

    def test_non_admin_returns_403(self, user_client):
        res = user_client.delete(f"{BASE}/auth/bans/1")
        assert res.status_code == 403


# ─────────────────────────────────────────────────────────────
# GET/DELETE /auth/invites
# ─────────────────────────────────────────────────────────────
class TestListInvites:
    _url = f"{BASE}/auth/invites"

    def test_success(self, admin_client):
        deps.db.query.return_value = [
            {"id": 1, "username": "new_user", "role": "user",
             "invite_token": "tok", "expires_at": _NOW, "created_at": _NOW}
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert len(res.json()["data"]) == 1

    def test_empty_list(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_non_admin_returns_403(self, user_client):
        res = user_client.get(self._url)
        assert res.status_code == 403


class TestRevokeInvite:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{BASE}/auth/invites/1")
        assert res.status_code == 204

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{BASE}/auth/invites/999")
        assert res.status_code == 404

    def test_non_admin_returns_403(self, user_client):
        res = user_client.delete(f"{BASE}/auth/invites/1")
        assert res.status_code == 403


# ─────────────────────────────────────────────────────────────
# POST /auth/users/{user_id}/unlock
# ─────────────────────────────────────────────────────────────
class TestUnlockUser:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},   # guild membership check
            _USER_ROW,   # after unlock (profile return)
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.post(f"{BASE}/auth/users/2/unlock")
        assert res.status_code == 200

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.post(f"{BASE}/auth/users/999/unlock")
        assert res.status_code == 404

    def test_non_admin_returns_403(self, user_client):
        res = user_client.post(f"{BASE}/auth/users/2/unlock")
        assert res.status_code == 403


# ─────────────────────────────────────────────────────────────
# POST /auth/users/{user_id}/ban + /unban
# ─────────────────────────────────────────────────────────────
class TestBanUser:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"username": "target_user"},  # user lookup
            _USER_ROW,                    # after ban (profile return)
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.post(f"{BASE}/auth/users/2/ban")
        assert res.status_code == 200

    def test_self_ban_returns_400(self, admin_client):
        # ADMIN["id"] = 1: 自分自身をBAN不可
        res = admin_client.post(f"{BASE}/auth/users/1/ban")
        assert res.status_code == 400

    def test_user_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.post(f"{BASE}/auth/users/999/ban")
        assert res.status_code == 404

    def test_non_admin_returns_403(self, user_client):
        res = user_client.post(f"{BASE}/auth/users/2/ban")
        assert res.status_code == 403


class TestUnbanUser:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"username": "target_user"},  # user lookup
            _USER_ROW,                    # after unban (profile return)
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.post(f"{BASE}/auth/users/2/unban")
        assert res.status_code == 200

    def test_user_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.post(f"{BASE}/auth/users/999/unban")
        assert res.status_code == 404

    def test_non_admin_returns_403(self, user_client):
        res = user_client.post(f"{BASE}/auth/users/2/unban")
        assert res.status_code == 403


# ─────────────────────────────────────────────────────────────
# GET /auth/users/{user_id}/profile
# ─────────────────────────────────────────────────────────────
class TestGetUserProfile:
    def test_admin_can_view_any_profile(self, admin_client):
        deps.db.query_one.return_value = _USER_ROW
        deps.db.query.return_value = []

        res = admin_client.get(f"{BASE}/auth/users/2/profile")
        assert res.status_code == 200
        body = res.json()
        assert "user" in body
        assert "created_odai" in body
        assert "created_tags" in body

    def test_user_can_view_own_profile(self, user_client):
        # USER["id"] = 2 → 自分自身のプロフィールは閲覧可
        deps.db.query_one.return_value = _USER_ROW
        deps.db.query.return_value = []

        res = user_client.get(f"{BASE}/auth/users/2/profile")
        assert res.status_code == 200

    def test_user_cannot_view_others_profile(self, user_client):
        # USER["id"] = 2, user_id=1 (別ユーザー) → 403
        res = user_client.get(f"{BASE}/auth/users/1/profile")
        assert res.status_code == 403

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None
        deps.db.query.return_value = []

        res = admin_client.get(f"{BASE}/auth/users/999/profile")
        assert res.status_code == 404

    def test_profile_includes_odai_and_tags(self, admin_client):
        deps.db.query_one.return_value = _USER_ROW
        deps.db.query.side_effect = [
            [{"id": 1, "filename": "odai1.jpg", "is_favorite": 0, "added_at": _NOW}],
            [{"id": 1, "name": "日常", "description": None, "is_favorite": 0, "created_at": _NOW}],
        ]

        res = admin_client.get(f"{BASE}/auth/users/2/profile")
        assert res.status_code == 200
        body = res.json()
        assert len(body["created_odai"]) == 1
        assert len(body["created_tags"]) == 1


# ─────────────────────────────────────────────────────────────
# GET /auth/users (非管理者パス)
# ─────────────────────────────────────────────────────────────
class TestListUsersNonAdmin:
    _url = f"{BASE}/auth/users"

    def test_non_admin_sees_only_own_data(self, user_client):
        deps.db.query.return_value = [_USER_ROW]

        res = user_client.get(self._url)
        assert res.status_code == 200
        assert len(res.json()) == 1


# ─────────────────────────────────────────────────────────────
# PUT /auth/users/{user_id} (追加シナリオ)
# ─────────────────────────────────────────────────────────────
class TestUpdateUserExtra:
    def test_non_admin_cannot_update_other_user(self, user_client):
        # USER["id"] = 2, user_id=1 → 403
        res = user_client.put(
            f"{BASE}/auth/users/1",
            json={"display_name": "hacker"},
        )
        assert res.status_code == 403

    def test_wrong_current_password_returns_401(self, user_client):
        deps.db.query_one.side_effect = [
            {"id": 2},                                          # guild membership check
            {"password_hash": hash_password("real_pass")},      # password hash lookup
        ]
        deps.db.execute.return_value = make_cursor()

        res = user_client.put(
            f"{BASE}/auth/users/2",
            json={"password": "newpassword123", "current_password": "wrong_pass"},
        )
        assert res.status_code == 401

    def test_missing_current_password_returns_400(self, user_client):
        deps.db.query_one.return_value = {"id": 2}  # guild membership check
        deps.db.execute.return_value = make_cursor()

        res = user_client.put(
            f"{BASE}/auth/users/2",
            json={"password": "newpassword123"},  # current_password 未指定
        )
        assert res.status_code == 400

    def test_admin_can_change_role(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 2},   # guild membership check
            _USER_ROW,   # after update
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(
            f"{BASE}/auth/users/2",
            json={"role": "admin"},
        )
        assert res.status_code == 200
