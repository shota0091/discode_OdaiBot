"""設定 API の追加エンドポイントテスト。

/settings/name（認証不要）と /settings/channels（認証必要）を検証する。
"""
from __future__ import annotations

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, GUILD_ID


class TestGetGuildName:
    _url = f"{BASE}/settings/name"

    def test_success(self, anon_client):
        deps.db.query_one.return_value = {"guild_name": "Test Server"}

        res = anon_client.get(self._url)
        assert res.status_code == 200
        assert res.json()["guild_name"] == "Test Server"

    def test_not_registered_returns_null(self, anon_client):
        deps.db.query_one.return_value = None

        res = anon_client.get(self._url)
        assert res.status_code == 200
        assert res.json()["guild_name"] is None

    def test_no_auth_required(self, anon_client):
        """認証ヘッダーなしでもアクセス可能。"""
        deps.db.query_one.return_value = {"guild_name": "Public Server"}

        res = anon_client.get(self._url)
        assert res.status_code == 200


class TestGetChannels:
    _url = f"{BASE}/settings/channels"

    def test_success(self, admin_client):
        deps.db.query.return_value = [
            {"channel_id": 987654321, "name": "general"},
            {"channel_id": 123456789, "name": "bot-channel"},
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 2
        assert data[0]["channel_id"] == "987654321"
        assert data[0]["name"] == "general"

    def test_empty_returns_empty_list(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_channel_id_is_string(self, admin_client):
        deps.db.query.return_value = [{"channel_id": 111222333444, "name": "ch"}]

        res = admin_client.get(self._url)
        assert isinstance(res.json()["data"][0]["channel_id"], str)

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401
