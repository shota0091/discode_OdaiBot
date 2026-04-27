"""設定 API (/settings/) のテスト。"""
from __future__ import annotations

from datetime import datetime

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, GUILD_ID, make_cursor

_NOW = datetime.utcnow()
_SETTINGS_ROW = {
    "guild_id": GUILD_ID,
    "bot_enabled": 1,
    "timezone": "Asia/Tokyo",
    "updated_at": _NOW,
}


class TestGetSettings:
    _url = f"{BASE}/settings/"

    def test_success(self, admin_client):
        deps.db.query_one.return_value = _SETTINGS_ROW

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["bot_enabled"] is True
        assert data["timezone"] == "Asia/Tokyo"

    def test_returns_defaults_when_no_row(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["bot_enabled"] is True
        assert data["timezone"] == "Asia/Tokyo"
        assert data["updated_at"] is None

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401


class TestUpdateSettings:
    _url = f"{BASE}/settings/"

    def test_update_existing(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},          # existing check
            _SETTINGS_ROW,      # after update
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(self._url, json={"bot_enabled": False})
        assert res.status_code == 200
        assert res.json()["data"]["bot_enabled"] is True  # row mock returns 1

    def test_insert_when_not_exists(self, admin_client):
        deps.db.query_one.side_effect = [
            None,           # existing check → not found
            _SETTINGS_ROW,  # after insert
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(self._url, json={"timezone": "UTC"})
        assert res.status_code == 200

    def test_non_admin_returns_403(self, user_client):
        res = user_client.put(self._url, json={"bot_enabled": True})
        assert res.status_code == 403
