"""グローバル認証 API (/api/auth/*) のテスト。

guild_id 非依存のログインとサーバー一覧取得を検証する。
"""
from __future__ import annotations

import pytest

from OdaiBotAPI import deps
from OdaiBotAPI.deps import hash_password

from .conftest import GUILD_ID, make_cursor

_USER_ROW = {
    "id": 1,
    "username": "admin_user",
    "display_name": None,
    "password_hash": "",  # 各テストで上書き
}
_GUILD_ROW = {
    "guild_id": GUILD_ID,
    "role": "admin",
    "guild_name": "Test Server",
}


class TestGlobalLogin:
    _url = "/api/auth/login"

    def test_success(self, anon_client):
        password = "password123"
        deps.db.query_one.return_value = {**_USER_ROW, "password_hash": hash_password(password)}
        deps.db.execute.return_value = make_cursor()
        deps.db.query.return_value = [_GUILD_ROW]

        res = anon_client.post(self._url, json={"username": "admin_user", "password": password})

        assert res.status_code == 200
        body = res.json()
        assert body["token_type"] == "bearer"
        assert "access_token" in body
        assert len(body["guilds"]) == 1
        assert body["guilds"][0]["guild_id"] == str(GUILD_ID)
        assert body["guilds"][0]["role"] == "admin"

    def test_wrong_password_returns_401(self, anon_client):
        deps.db.query_one.return_value = {**_USER_ROW, "password_hash": hash_password("real_pass")}

        res = anon_client.post(self._url, json={"username": "admin_user", "password": "wrong"})
        assert res.status_code == 401

    def test_user_not_found_returns_401(self, anon_client):
        deps.db.query_one.return_value = None

        res = anon_client.post(self._url, json={"username": "nobody", "password": "pass"})
        assert res.status_code == 401

    def test_no_guilds_returns_403(self, anon_client):
        password = "password123"
        deps.db.query_one.return_value = {**_USER_ROW, "password_hash": hash_password(password)}
        deps.db.execute.return_value = make_cursor()
        deps.db.query.return_value = []  # 所属ギルドなし

        res = anon_client.post(self._url, json={"username": "admin_user", "password": password})
        assert res.status_code == 403

    def test_display_name_in_response(self, anon_client):
        password = "password123"
        deps.db.query_one.return_value = {
            **_USER_ROW,
            "password_hash": hash_password(password),
            "display_name": "管理者",
        }
        deps.db.execute.return_value = make_cursor()
        deps.db.query.return_value = [_GUILD_ROW]

        res = anon_client.post(self._url, json={"username": "admin_user", "password": password})
        assert res.status_code == 200
        assert res.json()["display_name"] == "管理者"


class TestListGuilds:
    _url = "/api/auth/guilds"

    def test_success(self, anon_client):
        deps.db.query.return_value = [_GUILD_ROW]

        res = anon_client.get(self._url, headers={"Authorization": "Bearer valid_token"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["guild_id"] == str(GUILD_ID)
        assert data[0]["guild_name"] == "Test Server"

    def test_no_token_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401

    def test_invalid_token_returns_401(self, anon_client):
        deps.db.query.return_value = []  # トークンに合致するユーザーなし

        res = anon_client.get(self._url, headers={"Authorization": "Bearer bad_token"})
        assert res.status_code == 401

    def test_multiple_guilds(self, anon_client):
        deps.db.query.return_value = [
            {"guild_id": GUILD_ID, "role": "admin", "guild_name": "Server A"},
            {"guild_id": 999888777, "role": "user", "guild_name": "Server B"},
        ]

        res = anon_client.get(self._url, headers={"Authorization": "Bearer token"})
        assert res.status_code == 200
        assert len(res.json()["data"]) == 2
