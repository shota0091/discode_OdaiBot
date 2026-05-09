"""タグ詳細 API (/{tag_id}/detail) のテスト。"""
from __future__ import annotations

from datetime import datetime

import pytest

from OdaiBotAPI import deps

from .conftest import BASE

_NOW = datetime.utcnow()

_TAG_ROW = {
    "id": 1, "name": "日常", "description": "普段使い",
    "is_favorite": 0, "created_at": _NOW, "updated_at": _NOW,
    "created_by": 1, "created_by_name": "admin",
}


class TestGetTagDetail:
    _url = f"{BASE}/tags/1/detail"

    def test_success(self, admin_client):
        deps.db.query_one.return_value = _TAG_ROW
        deps.db.query.side_effect = [[], []]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["name"] == "日常"
        assert "odai" in data
        assert "schedules" in data

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.get(self._url)
        assert res.status_code == 404

    def test_includes_odai_list(self, admin_client):
        deps.db.query_one.return_value = _TAG_ROW
        deps.db.query.side_effect = [
            [{"id": 1, "filename": "photo.jpg", "tagged_at": _NOW, "tagged_by_name": "admin"}],
            [],
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert len(res.json()["data"]["odai"]) == 1
        assert res.json()["data"]["odai"][0]["filename"] == "photo.jpg"

    def test_includes_schedules_with_enabled_as_bool(self, admin_client):
        deps.db.query_one.return_value = _TAG_ROW
        deps.db.query.side_effect = [
            [],
            [{"id": 1, "time": "08:00", "enabled": 1, "tag_mode": "allow", "channel_name": "general"}],
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        sched = res.json()["data"]["schedules"][0]
        assert sched["enabled"] is True

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401
